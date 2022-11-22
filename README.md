# RocketBooster ✨🚀✨

TL;DR: *RocketBooster* is a simple training environment equipped with optimization algorithms such as reinforcement learning, genetic optimization, and simulated annealing to learn to propulsively land an orbital rocket booster.

## Introduction

<p align="center">
    <img src="docs/booster.png" width="240" height=""/>
</p>

- The booster's goal is to reach the landing pad at a velocity smaller or equal to $v_{\text{max}}$.
- Boosters are equipped with neural networks for thrust control.

Inspired by SpaceX's incredible progress, I set up a simple environment that uses PyBox2D for rigid physics simulation and PyGame for rendering and visualization, that allows to use different methods to land a booster in a physical simulation.

The physics is modeled using PyBox2D, a 2D physics library for rigid physics simulations. The booster consists of three sections. A long and low density section (the booster's hull containing mostly empty fuel tanks) connected to a short high density section (the booster's engines). On top of that there are the landing legs which are modeled as medium density sticks attached to the lower part of the rocket in a 45 degree angle.

The landing of the booster is learned using a genetic algorithm to optimize a small neural network, the booster's brain. The network's input are the booster's current height (x, y), speed (vx, vy), acceleration (ax, ay) and remaining fuel (maybe in a later stage).

This project can also be tackled with deep reinforcement learning (e.g. deep Q-learning).

## Run Examples

```console
cd rocketbooster
python -m projects.evolution_strategies.main
python -m projects.genetic_optimization.main
python -m projects.reinforcement_learning.main
python -m projects.simulated_annealing.main
```

## Methods

### Reward Function

- Number of simulation steps (time restriction) acts as an implicit fuel restriction. Thus, the booster is rewarded for landing quickly.
- Accumulate rewards vs. final reward

### Genetic Optimization

- Uses simple mutation operation

### Evolution Strategies

The evolution strategies (ES) optimization estimates gradients

- In the past, ES has achieved strong results on RL benchmarks.
- ES is easy to implement and can be massively scaled.
- In its core, the ES algorithm resembles simple hill-climbing in a high-dimensional space. 
- ES uses *finite differences* along a few random directions at each optimization step to estimate the gradients. 
- No need for backpropagation
- Parameter centric reinforcement learning.
- ES also allows to use a continuous action space.

### Simulated Annealing

- Run neighbor state in parallel
    - Only works for random starting point for each agent
- Select best agent

### Reinforcement Learning

Here we use Deep Q-Learning which is one of the core concepts in Reinforcement Learning (RL).

The implemented Deep Q-Learning algorithm uses a batch of episodes to learn a policy that maximizes the reward.

- NOTE: Run N agents in parallel and record their episodes.

- We use a policy function (e.g. a neural network resembling the agent's brain), to compute what an agent is supposed to do in any given situation.

- The neural network takes the current state of its environment (position, velocity, angle, angular velocity) as input and outputs the probability of taking one of the allowed actions. 

- We can use Deep Q-Learning to learn a control policy to land our booster.

- Using Deep Q-Learning, we use a deep neural network to predict the expected utility (also Q-value) of executing an action in a given state.

- Training process
    - We start the training process with a random initialization of the policy (the neural network)
    - While the agent interacts with the environment, we record the produced data at each time step. These data are the current state, the agent's performed action, and the reward received.
    - Given the set of state-action-reward pairs, we can use backpropagation to encourage state-actions pairs that resulted in a positive or high reward discourage pairs with negative or low reward.
    - During the training process, we enforce a certain degree of exploration by injecting noise to the actions of the agent. Exploration is induced by sampling from the action distribution at each time step.


#### Deep Q-Learning

- Deep Q-Learning, Policy Gradients are model-free learning algorithms as they do not use the transition probability distribution (and the reward function) associated with the Markov decision process (MDP), which, in RL, represents the problem to be solved. That means, RL algorithms do not learn a model of their environment's transition function to make predictions of future states and rewards.

- Model-free RL always needs to take an action before it can make predictions about the next state and reward.

- Model-free RL means, that the agent does not have access to a model of the environment. Here, the environment is a function used to predict state transition and rewards.

- Deep Q-Learning uses a trial and error method to learn about the environment it interacts with. This is also called exploration. 

- Q-Value is the maximum expected reward an agent can reach by taken a certain action $A$ in state $S$.

#### Pseudo Code
The following pseudo code illustrates the training procedure used for Deep Q-Learning:

```python
def train(num_epochs: int, batch_size: int):

    reward = 0.0

    for epoch in range(num_epochs):

        running_reward = 0.0
        running_loss = []
        running_counter = 0

        # Get state of booster at beginning of simulation
        self.booster.reset()
        state = self.booster.get_state()

        is_alive = True  # True as long as simulation is ongoing (no crash, within boundary domain, etc..)
        while is_alive:

            # Select an action from the discrete action space.
            action = self.model.select_action()

            # Apply selected action to booster.
            self.env.apply_action(action)

            # Take a simulation step
            self.env.step()

            # Get state of booster (pos, vel, angle, angular velocity)
            state = self.booster.get_state()

            # Compute score 
            reward = self.env.comp_score()

            # Check if booster is active.
            is_alive = self.env.is_alive()

            # Memorize events.
            self.model.memorize(state, action, reward, new_state, is_alive)

            # Create replay batch from memory
            replay = random.sample(self.model.memory, min(len(self.model.memory), batch_size))

            # Create training set from replay
            x_data, y_data = self.model.create_training_set(replay)

            # Learn control policy
            pred = self.model.forward(x_data)
            loss = self.criterion(y_data, pred)  # e.g. MSE
            loss.backward()
            optimizer.step()

            state = new_state

            # TODO: Write to Tensorboard
            running_loss += loss.item()
            running_reward += reward
            running_counter += 1

        epoch_loss = running_loss / running_counter
        epsilon = epsilon_min + (1.0 - epsilon_min) * math.e ** (-decay_rate * epoch)
```

#### Memory Size

- Replay

#### Action Space

We select an action from a discrete action space (maximum thrust of an engine at a certain angle). At maximum thrust (only on or off), the discrete action space of the booster for five different angles covering $\{-10°,-5°,0°,5°,10°,\}$ looks as follows:

|#|Action|
|:---:|:---:|
|1|Main engine fire at -10°|
|2|Main engine fire at -5°|
|3|Main engine fire at 0°|
|...|...|
|6|Left engine fire at -10°|
|...|...|
|15|Right engine fire at 10°|


As we select one action a time, the action is an array with shape `(1,)`. For the action space above, the action can take values in the range from 0 to 14.

During training, we either choose a random action from our discrete action space, or we take the action with highest predicted utility predicted by the neural network for a given state.

#### State Space

The state (or observation) space is defined by the booster's position, velocity, angle, and angular velocity:

|Number|Observation|Minimum|Maximum|
|:---:|:---:|:---:|:---:|
|1|Position $r_x$|$r_{x,{\text{min}}}$|$r_{x,{\text{max}}}$|
|2|Position $r_y$|$r_{y,{\text{min}}}$|$r_{y,{\text{max}}}$|
|3|Velocity $v_x$|$v_{x,{\text{min}}}$|$v_{x,{\text{max}}}$|
|4|Velocity $v_y$|$v_{y,{\text{min}}}$|$v_{y,{\text{max}}}$|
|5|Angle $\theta$|$\theta_{\text{min}}$|$\theta_{\text{max}}$|
|6|Angular velocity $\omega$|$\omega_{\text{min}}$|$\omega_{\text{max}}$|

The ranges above are defined in the *config.yml* file.

Thus, an observation is an array with shape `(6,)`.

captures the booster's states within the simulation and is defined by the 

#### Parameters

- `epsilon` is the epsilon-greedy value. This value defines the probability, that the agent selects a random action instead of the action that maximizes the expected utility (Q-value).

- `decay_rate` determines the decay of the `epsilon` value after each epoch.

- `epsilon_min` minimum allowed value for `epsilon` during the training period.

- `gamma` is a discount factor that determines how much the agent considers future rewards.



## Installation

To run *RocketBooster*, install the latest master directly from GitHub. For a basic install, run:

```bash
git clone https://github.com/kaifishr/RocketBooster
cd RocketBooster 
pip install -r requirements.txt
```

Then start the optimization by running:
Start the training with genetic optimization by running the following command:

```bash
python -m projects.genetic_optimization.main
```

## TODOs

- Add project with deep reinforcement learning.


## References

- [PyBox2D](https://github.com/pybox2d/pybox2d) on GitHub
- [backends](https://github.com/pybox2d/pybox2d/tree/master/library/Box2D/examples/backends) for PyBox2D
- PyBox2D [tutorial](https://github.com/pybox2d/cython-box2d/blob/master/docs/source/getting_started.md)
- [Minimal PyBox2D examples](https://github.com/pybox2d/pybox2d/tree/master/library/Box2D/examples)
- Box2D C++ [documentation](https://box2d.org/documentation/)

## Citation

If you find this project useful, please use BibTeX to cite it as:

```bibtex
@misc{fischer2022rocketbooster,
  title={RocketBooster},
  author={Fischer, Kai},
  year={2022},
  howpublished={\url{https://github.com/kaifishr/RocketBooster}}
}
```

## License

MIT