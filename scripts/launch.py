import datetime
import json
import os

import click

AMI_MAP = {
    "us-east-2": os.environ.get("AWS_AMI", None),
}


def highlight(x):
    if not isinstance(x, str):
        x = json.dumps(x, sort_keys=True, indent=2)
    click.secho(x, fg='green')


def make_disable_hyperthreading_script():
    return """
# disable hyperthreading
# https://forums.aws.amazon.com/message.jspa?messageID=189757
for cpunum in $(
    cat /sys/devices/system/cpu/cpu*/topology/thread_siblings_list |
    sed 's/-/,/g' | cut -s -d, -f2- | tr ',' '\n' | sort -un); do
        echo 0 > /sys/devices/system/cpu/cpu$cpunum/online
done
"""


def make_download_and_run_script(cmd):
    return """su -l ubuntu <<'EOF'
set -x
cd ~/Git/neuroevolved-agents/
git pull
. env/bin/activate
cd es-distributed
{cmd}
EOF
""".format(cmd=cmd)


def make_master_script(exp_str, algo):
    cmd = """
cat > ~/experiment.json <<< '{exp_str}'
python -m es_distributed.main master \
    --master_socket_path /var/run/redis/redis.sock \
    --log_dir ~ \
    --exp_file ~/experiment.json \
    --algo {algo} 
    """.format(exp_str=exp_str, algo=algo)
    return """#!/bin/bash
{
set -x

%s

# Disable redis snapshots
echo 'save ""' >> /etc/redis/redis.conf

# Make the unix domain socket available for the master client
# (TCP is still enabled for workers/relays)
echo "unixsocket /var/run/redis/redis.sock" >> /etc/redis/redis.conf
echo "unixsocketperm 777" >> /etc/redis/redis.conf
mkdir -p /var/run/redis
chown ubuntu:ubuntu /var/run/redis

systemctl restart redis

%s
} >> /home/ubuntu/user_data.log 2>&1
""" % (make_disable_hyperthreading_script(), make_download_and_run_script(cmd))


def make_worker_script(master_private_ip, algo):
    cmd = ("MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "
           "python -m es_distributed.main workers "
           "--master_host {} "
           "--algo {} "
           "--relay_socket_path /var/run/redis/redis.sock").format(master_private_ip, algo)
    return """#!/bin/bash
{
set -x

%s

# Disable redis snapshots
echo 'save ""' >> /etc/redis/redis.conf

# Make redis use a unix domain socket and disable TCP sockets
sed -ie "s/port 6379/port 0/" /etc/redis/redis.conf
echo "unixsocket /var/run/redis/redis.sock" >> /etc/redis/redis.conf
echo "unixsocketperm 777" >> /etc/redis/redis.conf
mkdir -p /var/run/redis
chown ubuntu:ubuntu /var/run/redis

systemctl restart redis

%s
} >> /home/ubuntu/user_data.log 2>&1
""" % (make_disable_hyperthreading_script(), make_download_and_run_script(cmd))


@click.command()
@click.argument('exp_files', nargs=-1, type=click.Path(), required=True)
@click.option('--algorithm', required=True)
@click.option('--key_name', default=lambda: os.environ["KEY_NAME"])
@click.option('--aws_access_key_id', default=os.environ.get("AWS_ACCESS_KEY", None))
@click.option('--aws_secret_access_key', default=os.environ.get("AWS_ACCESS_SECRET", None))
@click.option('--archive_excludes', default=(".git", "__pycache__", ".idea", "scratch"))
@click.option('--spot_price')
@click.option('--region_name')
@click.option('--zone')
@click.option('--cluster_size', type=int, default=1)
@click.option('--spot_master', is_flag=True, help='Use a spot instance as the master')
@click.option('--master_instance_type')
@click.option('--worker_instance_type')
@click.option('--security_group')
@click.option('--yes', is_flag=True, help='Skip confirmation prompt')
def main(exp_files,
         algorithm,
         key_name,
         aws_access_key_id,
         aws_secret_access_key,
         archive_excludes,
         spot_price,
         region_name,
         zone,
         cluster_size,
         spot_master,
         master_instance_type,
         worker_instance_type,
         security_group,
         yes
         ):

    highlight('Launching:')
    highlight(locals())

    import boto3
    ec2 = boto3.resource(
        "ec2",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    as_client = boto3.client(
        'autoscaling',
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    for i_exp_file, exp_file in enumerate(exp_files):
        with open(exp_file, 'r') as f:
            exp = json.loads(f.read())
        highlight('Experiment [{}/{}]:'.format(i_exp_file + 1, len(exp_files)))
        highlight(exp)
        if not yes:
            click.confirm('Continue?', abort=True)

        exp_prefix = exp['exp_prefix']
        exp_str = json.dumps(exp)

        exp_name = '{}_{}'.format(exp_prefix, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))

        image_id = AMI_MAP[region_name]
        if image_id is None:
            image_id = os.environ.get("AWS_AMI", None)
        highlight('Using AMI: {}'.format(image_id))

        if spot_master:
            import base64
            requests = ec2.meta.client.request_spot_instances(
                SpotPrice=spot_price,
                InstanceCount=1,
                LaunchSpecification=dict(
                    ImageId=image_id,
                    KeyName=key_name,
                    InstanceType=master_instance_type,
                    EbsOptimized=True,
                    SecurityGroups=[security_group],
                    Placement=dict(
                        AvailabilityZone=zone,
                    ),
                    UserData=base64.b64encode(make_master_script(exp_str, algorithm).encode()).decode()
                )
            )['SpotInstanceRequests']
            assert len(requests) == 1
            request_id = requests[0]['SpotInstanceRequestId']
            # Wait for fulfillment
            highlight('Waiting for spot request {} to be fulfilled'.format(request_id))
            ec2.meta.client.get_waiter('spot_instance_request_fulfilled').wait(SpotInstanceRequestIds=[request_id])
            req = ec2.meta.client.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])
            master_instance_id = req['SpotInstanceRequests'][0]['InstanceId']
            master_instance = ec2.Instance(master_instance_id)
        else:
            master_instance = ec2.create_instances(
                ImageId=image_id,
                KeyName=key_name,
                InstanceType=master_instance_type,
                EbsOptimized=True,
                SecurityGroups=[security_group],
                MinCount=1,
                MaxCount=1,
                Placement=dict(
                    AvailabilityZone=zone,
                ),
                UserData=make_master_script(exp_str, algorithm)
            )[0]
        master_instance.create_tags(
            Tags=[
                dict(Key="Name", Value=exp_name + "-master"),
                dict(Key="es_dist_role", Value="master"),
                dict(Key="exp_prefix", Value=exp_prefix),
                dict(Key="exp_name", Value=exp_name),
            ]
        )
        highlight("Master created. IP: %s" % master_instance.public_ip_address)

        config_resp = as_client.create_launch_configuration(
            ImageId=image_id,
            KeyName=key_name,
            InstanceType=worker_instance_type,
            EbsOptimized=True,
            SecurityGroups=[security_group],
            LaunchConfigurationName=exp_name,
            UserData=make_worker_script(master_instance.private_ip_address, algorithm),
            SpotPrice=spot_price,
        )
        assert config_resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        asg_resp = as_client.create_auto_scaling_group(
            AutoScalingGroupName=exp_name,
            LaunchConfigurationName=exp_name,
            MinSize=cluster_size,
            MaxSize=cluster_size,
            DesiredCapacity=cluster_size,
            AvailabilityZones=[zone],
            DefaultCooldown=0,
            Tags=[
                dict(Key="Name", Value=exp_name + "-worker"),
                dict(Key="es_dist_role", Value="worker"),
                dict(Key="exp_prefix", Value=exp_prefix),
                dict(Key="exp_name", Value=exp_name),
            ]
            # todo: also try placement group to see if there is increased networking performance
        )
        assert asg_resp["ResponseMetadata"]["HTTPStatusCode"] == 200
        highlight("Scaling group created")

        highlight("%s launched successfully." % exp_name)
        highlight("Manage at %s" % (
            "https://%s.console.aws.amazon.com/ec2/v2/home?region=%s#Instances:sort=tag:Name" % (
            region_name, region_name)
        ))


if __name__ == '__main__':
    main()
