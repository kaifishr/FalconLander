"""Optimization class for simulated annealing."""
import copy
import math
import numpy
import random

from projects.src.optimizer import Optimizer

from src.utils.config import Config
from src.environment import Environment


class SimulatedAnnealing(Optimizer):
    """Optimizer class for asynchronous simulated annealing."""

    def __init__(self, environment: Environment, config: Config) -> None:
        """Initializes optimizer"""
        super().__init__()

        self.boosters = environment.boosters

        config = config.optimizer

        self.perturbation_probability_initial = config.perturbation_probability_initial
        self.perturbation_probability_final = config.perturbation_probability_final
        self.perturbation_rate_initial = config.perturbation_rate_initial
        self.perturbation_rate_final = config.perturbation_rate_final
        self.temp_initial = config.temp_initial
        self.temp_final = config.temp_final
        self.temp = self.temp_initial

        num_iterations = config.num_iterations
        self.gamma = (1.0 / num_iterations) * math.log(
            self.temp_initial / self.temp_final
        )

        self.parameters_old = copy.deepcopy(self.boosters[0].model.parameters)

        self.reward_old = 0.0
        self.iteration = 0
        self.idx_best = 0

    def _scheduler(self) -> None:
        """Decreases temperature according to exponential decay."""
        self.temp = self.temp_initial * math.exp(-self.gamma * self.iteration)
        if self.temp < self.temp_final:
            self.temp = self.temp_final

    def _perturb(self) -> None:
        """Perturb network parameters of each booster."""

        eta = self.temp / self.temp_initial

        pert_prob_init = self.perturbation_probability_initial
        pert_prob_final = self.perturbation_probability_final
        perturbation_prob = (pert_prob_init - pert_prob_final) * eta + pert_prob_final

        pert_rate_init = self.perturbation_rate_initial
        pert_rate_final = self.perturbation_rate_final
        perturbation_rate = (pert_rate_init - pert_rate_final) * eta + pert_rate_final

        for booster in self.boosters:
            booster.model.parameters = copy.deepcopy(self.parameters_old)
            self._perturb_weights(booster.model, perturbation_prob, perturbation_rate)

    @staticmethod
    def _perturb_weights(model: object, perturbation_prob: float, perturbation_rate: float) -> None:
        """Perturbs the network's weights."""

        for weight, bias in model.parameters:

            mask = numpy.random.random(size=weight.shape) < perturbation_prob
            mutation = perturbation_rate * numpy.random.normal(size=weight.shape)
            weight += mask * mutation

            mask = numpy.random.random(size=bias.shape) < perturbation_prob
            mutation = perturbation_rate * numpy.random.normal(size=bias.shape)
            bias += mask * mutation

    def step(self) -> None:
        """Runs single simulated annealing step."""

        # Select booster with highest reward in current population.
        # rewards = numpy.array([sum(booster.rewards) for booster in self.boosters])  
        rewards = numpy.array([booster.rewards[-1] for booster in self.boosters]) 
        self.idx_best = rewards.argmax()
        reward = rewards[self.idx_best]
        self.stats["reward"] = reward 

        delta_reward = reward - self.reward_old

        # Accept configuration if reward is higher or with probability p = exp(delta_reward / temp)
        if (delta_reward > 0) or (math.exp(delta_reward / self.temp) > random.random()):
            # Save network if current reward is higher
            self.parameters_old = copy.deepcopy(
                self.boosters[self.idx_best].model.parameters
            )
            self.reward_old = reward
        else:
            # Do not accept current state. Return to previous state.
            for booster in self.boosters:
                booster.model.parameters = copy.deepcopy(self.parameters_old)

        # Reduce temperature according to scheduler
        self._scheduler()

        # Perturb weights for next iteration.
        self._perturb()

        self.iteration += 1


class SimulatedAnnealing_(Optimizer):
    """Optimizer class for simulated annealing."""

    def __init__(self, environment: Environment, config: Config) -> None:
        """Initializes optimizer"""
        super().__init__()

        self.booster = environment.boosters[0]
        self.model = self.booster.model

        config = config.optimizer

        self.perturbation_probability_initial = config.perturbation_probability_initial
        self.perturbation_probability_final = config.perturbation_probability_final
        self.perturbation_rate_initial = config.perturbation_rate_initial
        self.perturbation_rate_final = config.perturbation_rate_final
        self.temp_initial = config.temp_initial
        self.temp_final = config.temp_final
        self.temp = self.temp_initial

        num_iterations = config.num_iterations
        self.gamma = (1.0 / num_iterations) * math.log(
            self.temp_initial / self.temp_final
        )

        self.parameters_old = copy.deepcopy(self.model.parameters)

        self.reward = 0.0
        self.reward_old = 0.0
        self.iteration = 0

    def _scheduler(self) -> None:
        """Decreases temperature according to exponential decay."""
        self.temp = self.temp_initial * math.exp(-self.gamma * self.iteration)
        if self.temp < self.temp_final:
            self.temp = self.temp_final

    def _perturb(self) -> None:
        """Perturbs network weights."""

        eta = self.temp / self.temp_initial

        pert_prob_init = self.perturbation_probability_initial
        pert_prob_final = self.perturbation_probability_final
        perturbation_prob = (pert_prob_init - pert_prob_final) * eta + pert_prob_final

        pert_rate_init = self.perturbation_rate_initial
        pert_rate_final = self.perturbation_rate_final
        perturbation_rate = (pert_rate_init - pert_rate_final) * eta + pert_rate_final

        for weight, bias in self.model.parameters:

            mask = numpy.random.random(size=weight.shape) < perturbation_prob
            mutation = perturbation_rate * numpy.random.normal(size=weight.shape)
            weight += mask * mutation

            mask = numpy.random.random(size=bias.shape) < perturbation_prob
            mutation = perturbation_rate * numpy.random.normal(size=bias.shape)
            bias += mask * mutation

    def step(self) -> None:
        """Runs single optimization step."""

        # Get reward of booster.
        self.reward = sum(self.booster.rewards)
        # self.reward = self.booster.rewards[-1]  # final reward
        self.stats["reward"] = self.reward
        self.stats["temperature"] = self.temp

        delta_reward = self.reward - self.reward_old

        # Accept configuration if reward is higher or with probability p = exp(delta_reward / temp)
        if (delta_reward > 0) or (math.exp(delta_reward / self.temp) > random.random()):
            # Save network if current reward is higher
            self.parameters_old = copy.deepcopy(self.model.parameters)
            self.reward_old = self.reward
        else:
            # Do not accept current state. Return to previous state.
            self.model.parameters = copy.deepcopy(self.parameters_old)

        # Reduce temperature according to scheduler
        self._scheduler()

        # Perturb weights for next iteration.
        self._perturb()

        self.iteration += 1