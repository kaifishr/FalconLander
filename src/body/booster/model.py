"""Contains neural network definitions.

The booster's brain represented by a feedforward neural network.
"""
from typing import Union
import math
import random
from collections import deque

import numpy
import numpy as np
import torch
import torch.nn as nn
from scipy.special import expit

from src.utils.config import Config
from src.utils.utils import load_checkpoint


class ModelLoader:
    """Loads NumPy or PyTorch neural network."""

    def __init__(self, config: Config) -> None:
        """Initializes Network wrapper."""
        self.config = config

    def __call__(self):
        """Loads and returns model.
        Args:
            lib: Library "numpy" or "pytorch".
        """
        lib = self.config.optimizer.lib

        # Instantiate network
        if lib == "numpy":
            model = NumpyNeuralNetwork(self.config)
        elif lib == "torch":
            model = TorchNeuralNetwork(self.config)
            model.train(False)
        else:
            raise NotImplementedError(f"Network for {lib} not implemented.")

        # Load pre-trained model
        if self.config.checkpoints.load_model:
            load_checkpoint(model=model, config=self.config)

        return model


class NumpyNeuralNetwork:
    """Neural network written with Numpy.

    Attributes:
        mutation_prob:
        mutation_rate:
        weights:
        biases:
    """

    def __init__(self, config: Config) -> None:
        """Initializes NeuralNetwork."""

        config = config.env.booster.neural_network

        in_features = config.num_dim_in
        out_features = config.num_dim_out
        hidden_features = config.num_dim_hidden
        num_hidden_layers = config.num_hidden_layers

        # nonlinearity = "leaky_relu"
        # nonlinearity = "sigmoid"
        nonlinearity = "tanh"

        # Install activation function
        self.act_fun = self._install_activation_function(nonlinearity)

        # Parameters
        self.parameters = []

        # Input layer weights
        size = (hidden_features, in_features)
        self.parameters.append(self._init_weights(size=size, nonlinearity=nonlinearity))

        # Hidden layer weights
        size = (hidden_features, hidden_features)
        for _ in range(num_hidden_layers):
            self.parameters.append(
                self._init_weights(size=size, nonlinearity=nonlinearity)
            )

        # Output layer weights
        size = (out_features, hidden_features)
        self.parameters.append(self._init_weights(size=size, nonlinearity="sigmoid"))

    def _install_activation_function(self, nonlinearity: str):
        """Installs activation function."""
        if nonlinearity == "leaky_relu":
            act_fun = lambda x: np.where(x > 0, x, 0.01 * x)
        elif nonlinearity == "sigmoid":
            act_fun = expit
        elif nonlinearity == "tanh":
            act_fun = np.tanh
        else:
            raise NotImplementedError(
                f"Initialization for '{nonlinearity}' not implemented."
            )
        return act_fun

    @staticmethod
    def _init_weights(size: tuple[int, int], nonlinearity: str) -> None:
        """Initializes model weights.

        Xavier normal initialization for feedforward neural networks described in
        'Understanding the difficulty of training deep feedforward neural networks'
        by Glorot and Bengio (2010).

            std = gain * (2 / (fan_in + fan_out)) ** 0.5

        """
        if nonlinearity == "leaky_relu":
            gain = math.sqrt(2.0 / (1.0 + 0.01**2))
        elif nonlinearity == "sigmoid":
            gain = 1.0
        elif nonlinearity == "tanh":
            gain = 5.0 / 3.0
        else:
            raise NotImplementedError(
                f"Initialization for '{nonlinearity}' not implemented."
            )
        std = gain * (2.0 / sum(size)) ** 0.5

        weights = np.random.normal(loc=0.0, scale=std, size=size)
        biases = np.zeros(shape=(size[0], 1))

        return weights, biases

    def state_dict(self) -> dict:
        """Returns a dictionary containing the network's weights and biases."""
        state = {"weights": self.weights, "biases": self.biases}
        return state

    def load_state_dict(self, state_dict: dict) -> None:
        """Loads state dict holding the network's weights and biases.

        NOTE: Method ignores parameter dimension. 
        """
        self.weights = state_dict["weights"]
        self.biases = state_dict["biases"]

    def __call__(self, x: numpy.ndarray):
        return self.forward(x)

    def eval(self):
        pass

    def forward(self, x: numpy.ndarray):
        """Feedforward state.

        Args:
            x: State of booster.
        """
        for weight, bias in self.parameters[:-1]:
            x = self.act_fun(np.matmul(x, weight.T) + bias.T)

        weight, bias = self.parameters[-1]
        x = expit(np.matmul(x, weight.T) + bias.T)[0, :]

        return x


class TorchNeuralNetwork(nn.Module):
    """Deep Q Reinforcement Learning Model.

    Simple fully-connected neural network for Deep Q reinforcement learning.

    Attributes:
    """

    def __init__(self, config: Config) -> None:
        """Initializes NeuralNetwork class."""
        super().__init__()

        self.num_engines = 3 
        self.num_thrust_levels = 3  # Thrust levels of engines. Minimum is 2 for on/off
        self.num_thrust_angles = 3  # Thrust angles of engines. Must be an odd number.
        self.num_states = 6  # State of booster (pos_x, pos_y, vel_x, vel_y, angle, angular_velocity)
        self.epsilon = 0.5  # TODO: Use epsilon decay method from optimizer()
        self.gamma = 0.99
        self.memory_size = 1000
        self.memory = deque()

        # Number of actions plus `do nothing` action.
        self.num_actions = 1 + self.num_engines * self.num_thrust_levels * self.num_thrust_angles

        config = config.env.booster.neural_network

        in_features = config.num_dim_in
        hidden_features = config.num_dim_hidden
        num_hidden_layers = config.num_hidden_layers
        out_features = self.num_actions 

        layers = [
            nn.Flatten(start_dim=0),
            nn.Linear(in_features=in_features, out_features=hidden_features),
            nn.Tanh(),
        ]

        for _ in range(num_hidden_layers):
            layers += [
                nn.Linear(in_features=hidden_features, out_features=hidden_features),
                nn.Tanh(),
            ]

        layers += [
            nn.Linear(in_features=hidden_features, out_features=out_features),
            nn.Sigmoid(),
        ]

        self.net = nn.Sequential(*layers)

        self.apply(self._init_weights)
        self._init_action_lookup()

    def _init_weights(self, module) -> None:
        if isinstance(module, nn.Linear):
            # torch.nn.init.normal_(module.weight, mean=0.0, std=0.5)
            gain = 5.0 / 3.0  # Gain for tanh nonlinearity.
            torch.nn.init.xavier_normal_(module.weight, gain=gain)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)

    def _init_action_lookup(self):
        """Creates an action lookup table for discrete actions.

        TODO: Check thrust angles for number of angles = 1.
        """
        self.actions_lookup = {}

        thrust_levels = numpy.linspace(1.0 / self.num_thrust_levels, 1.0, self.num_thrust_levels)
        thrust_angles = numpy.linspace(0.0, 1.0, self.num_thrust_angles)

        if self.num_thrust_angles == 1:
            thrust_angles = numpy.array([0.5])

        n = 0
        # Add actions to look-up table.
        for i in range(self.num_engines):
            for j in range(self.num_thrust_levels):
                for k in range(self.num_thrust_angles):
                    # Action vector with thrust and angle information for each engine.
                    action = np.zeros((self.num_engines * 2)) 
                    # Select thrust for engine i
                    action[2*i] = thrust_levels[j]
                    # Select angle for engine i
                    action[2*i+1] = thrust_angles[k]  
                    self.actions_lookup[n] = action
                    n += 1

        # Add `do nothing` action.
        action = np.zeros((self.num_engines * 2)) 
        self.actions_lookup[n] = action

    def _memorize(self, state: torch.Tensor, action: int, reward: float = -1) -> None:
        """Stores past events.

        Stores current `state`, `action` based on state, and `reward`
        the followed from the performed action. 
        """
        self.memory.append([state, action, reward])
        # Make sure that the memory is not exceeded.
        if len(self.memory) > self.memory_size:
            self.memory.popleft()

    @torch.no_grad()
    def _select_action(self, state: torch.Tensor) -> int:
        """Selects an action from a discrete action space.

        Action is random with probability `epsilon` to encourage exploration.

        Args:
            epsilon: Probability of choosing a random action (epsilon-greedy value).

        Returns:
            Action to be performed by booster (Firing engine at certain angle).
        """
        if random.random() < self.epsilon:
            # Choose a random action
            action = random.randint(0, self.num_actions - 1)
            print(f"random {action = }")
        else:
            # Select action with highest predicted utility given state
            with torch.no_grad():  # Use decorator for method
                # self.eval()
                pred = self.net(state)
                action = torch.argmax(pred).item()
                # self.train()
            print(f"network {action = }")

        # Add state-action pair to memory
        self._memorize(state=state, action=action)

        # Convert action to action vector
        action = self.actions_lookup[action]

        return action

    def forward(self, state: list) -> Union[torch.Tensor, int]:
        """Forward method receives current state and predicts an action.

        Args:
            x: Current state.

        Returns:
            Action vector.
        """
        print(f"forward() {self.training = }")
        state = torch.from_numpy(state).float()

        if self.training:
            print("training")
            action = self.net(state)
        else:
            print("exploration")
            action = self._select_action(state)

        return action