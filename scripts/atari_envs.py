import gym
import atari_py as ap

all_envs = gym.envs.registry.all()
env_ids = [env_spec.id for env_spec in all_envs]
env_ids = [x for x in env_ids if '-ram' not in x]
env_ids = [x for x in env_ids if 'Deterministic' not in x]
env_ids = [x for x in env_ids if 'NoFrameskip' in x]

atari_games = ap.list_games()
env_ids = [x for x in env_ids if any(game.replace('_', '') in x.lower() for game in atari_games)]
env_ids = [x for x in env_ids if 'v4' in x]

action_meanings = [(x, gym.make(x).unwrapped.get_action_meanings()) for x in env_ids]
for pair in action_meanings:
    print(pair[0], *pair[1])

#print([game for game in atari_games if all(game.replace('_', '') not in x.lower() for x in env_ids)])
# ['kaboom', 'adventure', 'defender']  # these games are missing from gym
