import torch
import torch.nn as nn


class DQN(nn.Module):

    def __init__(self, state_size=14, action_size=5):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(state_size, 128),
            nn.ReLU(),

            nn.Linear(128, 128),
            nn.ReLU(),

            nn.Linear(128, action_size)
        )

    def forward(self, state):
        return self.network(state)

