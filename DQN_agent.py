import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from Dqn import DQN


class DQNAgent:

    def __init__(self, state_size=14, action_size=5):

        self.state_size = state_size
        self.action_size = action_size

        self.gamma = 0.95
        self.learning_rate = 0.001

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.model = DQN(
            state_size=self.state_size,
            action_size=self.action_size
        ).to(self.device)

        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.learning_rate
        )

        self.loss_function = nn.MSELoss()

    def choose_action(self, state):

        state_tensor = torch.tensor(
            state,
            dtype=torch.float32,
            device=self.device
        ).unsqueeze(0)

        with torch.no_grad():
            q_values = self.model(state_tensor)

        action = torch.argmax(q_values, dim=1).item()

        return action
    def train_step(self, batch):

        states = []
        actions = []
        rewards = []
        next_states = []
        dones = []

        states, actions, rewards, next_states, dones = zip(*batch)

        # Convert to NumPy arrays first to handle uniform memory layout safely
        states = torch.as_tensor(np.array(states), dtype=torch.float32, device=self.device)
        actions = torch.as_tensor(actions, dtype=torch.long, device=self.device)
        rewards = torch.as_tensor(rewards, dtype=torch.float32, device=self.device)
        next_states = torch.as_tensor(np.array(next_states), dtype=torch.float32, device=self.device)
        dones = torch.as_tensor(dones, dtype=torch.float32, device=self.device)

        # Q(s, a)
        current_q_values = self.model(states)

        current_q_values = current_q_values.gather(
            1,
            actions.unsqueeze(1)
        ).squeeze(1)

        # max Q(s', a')
        with torch.no_grad():

            next_q_values = self.model(next_states)

            max_next_q_values = next_q_values.max(
                dim=1
            ).values

            target_q_values = (
                rewards
                + self.gamma * max_next_q_values * (1 - dones)
            )

        # Calculate loss
        loss = self.loss_function(
            current_q_values,
            target_q_values
        )

        # Update network
        self.optimizer.zero_grad()

        loss.backward()

        self.optimizer.step()

        return loss.item()