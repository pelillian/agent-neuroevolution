## Neuroevolved Agents

This repo is based on code from [OpenAI](https://github.com/openai/evolution-strategies-starter) and [Uber Research](https://github.com/uber-research/deep-neuroevolution).

Ubuntu:
```
python3 -m venv env
. env/bin/activate

pip install -r requirements.txt
pip install gym[atari]

sudo apt install redis-server
. scripts/local_run_redis.sh
. scripts/local_run_exp.sh nsr-es configurations/multienv_nsres.json 72

```
