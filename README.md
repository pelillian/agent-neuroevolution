## Neuroevolved Agents

This repo is based on the code from [OpenAI](https://github.com/openai/evolution-strategies-starter) and [Uber Research](https://github.com/uber-research/deep-neuroevolution).

## How to run locally

clone repo

```
git clone https://github.com/uber-common/deep-neuroevolution.git
```

create python3 virtual env

```
python3 -m venv env
. env/bin/activate
```

install requirements
```
pip install -r requirements.txt
```
If you plan to use the mujoco env, make sure to follow [mujoco-py](https://github.com/openai/mujoco-py)'s readme about how to install mujoco correctly

launch redis
```
. scripts/local_run_redis.sh
```

launch sample ES experiment
```
. scripts/local_run_exp.sh es configurations/frostbite_es.json  # For the Atari game Frostbite
. scripts/local_run_exp.sh es configurations/humanoid.json  # For the MuJoCo Humanoid-v1 environment
```

launch sample NS-ES experiment
```
. scripts/local_run_exp.sh ns-es configurations/frostbite_nses.json
. scripts/local_run_exp.sh ns-es configurations/humanoid_nses.json
```

launch sample NSR-ES experiment
```
. scripts/local_run_exp.sh nsr-es configurations/frostbite_nsres.json
. scripts/local_run_exp.sh nsr-es configurations/humanoid_nsres.json
```

launch sample GA experiment
```
. scripts/local_run_exp.sh ga configurations/frostbite_ga.json  # For the Atari game Frostbite
```

launch sample Random Search experiment
```
. scripts/local_run_exp.sh rs configurations/frostbite_ga.json  # For the Atari game Frostbite
```


visualize results by running a policy file
```
python -m scripts.viz 'FrostbiteNoFrameskip-v4' <YOUR_H5_FILE>
python -m scripts.viz 'Humanoid-v1' <YOUR_H5_FILE>
```
