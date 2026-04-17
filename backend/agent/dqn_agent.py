import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
from utils.config import *


class DuelingDQN(nn.Module):
    """
    Dueling DQN architecture:
    - Shared feature extractor
    - Separate Value stream (V) and Advantage stream (A)
    - Q(s,a) = V(s) + A(s,a) - mean(A(s,:))
    Proven to improve sample efficiency by ~20-30% over standard DQN.
    """
    def __init__(self, state_size, action_size):
        super().__init__()
        # Shared feature extractor — bigger network with BatchNorm
        self.feature = nn.Sequential(
            nn.Linear(state_size, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
        )
        # Value stream: estimates V(s)
        self.value_stream = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        # Advantage stream: estimates A(s,a) for each action
        self.advantage_stream = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_size)
        )

    def forward(self, x):
        # Handle both single state (shape [state_size]) and batches ([B, state_size])
        single = (x.dim() == 1)
        if single:
            x = x.unsqueeze(0)   # [state_size] -> [1, state_size]
        features = self.feature(x)
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        # Q = V + (A - mean(A))
        q_values = value + (advantage - advantage.mean(dim=1, keepdim=True))
        if single:
            q_values = q_values.squeeze(0)  # [1, actions] -> [actions]
        return q_values


class DQNAgent:
    def __init__(self, state_size, action_size):
        self.action_size = action_size
        self.epsilon = EPSILON_START
        # Larger replay buffer: 50,000 transitions (was 5,000)
        self.memory = deque(maxlen=50000)
        # Online and target networks (Dueling DQN)
        self.model = DuelingDQN(state_size, action_size)
        self.target_model = DuelingDQN(state_size, action_size)
        self.target_model.load_state_dict(self.model.state_dict())
        self.target_model.eval()
        self.optimizer = optim.Adam(self.model.parameters(), lr=LEARNING_RATE)
        self.loss_fn = nn.SmoothL1Loss()   # Huber loss — more stable than MSE

    def update_target_network(self, soft=False, tau=0.01):
        """Hard or soft target network update."""
        if soft:
            # Soft update: θ_target = τ*θ_online + (1-τ)*θ_target
            for target_param, param in zip(self.target_model.parameters(), self.model.parameters()):
                target_param.data.copy_(tau * param.data + (1.0 - tau) * target_param.data)
        else:
            self.target_model.load_state_dict(self.model.state_dict())

    def act(self, state):
        if random.random() < self.epsilon:
            return random.randrange(self.action_size)
        with torch.no_grad():
            return torch.argmax(self.model(torch.FloatTensor(state))).item()

    def remember(self, s, a, r, s_, d):
        self.memory.append((s, a, r, s_, d))

    def replay(self, batch=128):
        if len(self.memory) < batch:
            return

        samples = random.sample(self.memory, batch)
        states      = torch.FloatTensor(np.array([s[0] for s in samples]))
        actions     = torch.LongTensor(np.array([s[1] for s in samples])).unsqueeze(1)
        rewards     = torch.FloatTensor(np.array([s[2] for s in samples]))
        next_states = torch.FloatTensor(np.array([s[3] for s in samples]))
        dones       = torch.FloatTensor(np.array([s[4] for s in samples]))

        # ---- Double DQN ----
        # 1. Use ONLINE model to SELECT best next action
        with torch.no_grad():
            next_actions = self.model(next_states).argmax(dim=1, keepdim=True)
            # 2. Use TARGET model to EVALUATE that action (reduces overestimation)
            next_q_values = self.target_model(next_states).gather(1, next_actions).squeeze(1)
            targets = rewards + (1 - dones) * GAMMA * next_q_values

        q_values = self.model(states).gather(1, actions).squeeze(1)

        loss = self.loss_fn(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping — prevents exploding gradients
        nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)
        self.optimizer.step()

        # Epsilon decay
        self.epsilon = max(EPSILON_MIN, self.epsilon * EPSILON_DECAY)

    def save(self, path):
        torch.save(self.model.state_dict(), path)

    def load(self, path):
        checkpoint = torch.load(path, map_location='cpu')
        model_dict = self.model.state_dict()
        
        # Handle shape mismatches for feature.0.weight dynamically
        for k in ['feature.0.weight']:
            if k in checkpoint and k in model_dict:
                chk_shape = checkpoint[k].shape
                mod_shape = model_dict[k].shape
                if chk_shape != mod_shape:
                    print(f"⚠️ Warning: Shape mismatch for {k}. Checkpoint: {chk_shape}, Current: {mod_shape}.")
                    if chk_shape[0] == mod_shape[0] and chk_shape[1] < mod_shape[1]:
                        # Pad with zeros for new features
                        pad_size = mod_shape[1] - chk_shape[1]
                        print(f"🔄 Padding {k} with {pad_size} column(s) of zeros.")
                        padded_weight = torch.cat([checkpoint[k], torch.zeros(chk_shape[0], pad_size, device=checkpoint[k].device)], dim=1)
                        checkpoint[k] = padded_weight
                    elif chk_shape[0] == mod_shape[0] and chk_shape[1] > mod_shape[1]:
                        # Truncate if current model is smaller
                        print(f"🔄 Truncating {k} to fit current model.")
                        checkpoint[k] = checkpoint[k][:, :mod_shape[1]]

        model_dict.update(checkpoint)
        self.model.load_state_dict(model_dict, strict=False)
        self.model.eval()
        self.target_model.load_state_dict(self.model.state_dict())
        self.target_model.eval()
