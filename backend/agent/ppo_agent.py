import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
import numpy as np
import os
from utils.config import *

class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(ActorCritic, self).__init__()
        
        # ACTOR: Decides Mean and Std of Action
        self.actor = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, action_dim),
            nn.Tanh() # Output -1 to 1 for Mean
        )
        
        # Learnable Log Std
        self.log_std = nn.Parameter(torch.zeros(action_dim))
        
        # CRITIC: Estimates Value of State
        self.critic = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.Tanh(),
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, 1)
        )
        
    def forward(self, state):
        value = self.critic(state)
        mean = self.actor(state)
        std = self.log_std.exp().expand_as(mean)
        dist = Normal(mean, std)
        return dist, value

class PPOAgent:
    def __init__(self, state_dim, action_dim, force_cpu=False):
        if force_cpu:
            self.device = torch.device("cpu")
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy = ActorCritic(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=PPO_LEARNING_RATE)
        self.experience_buffer = []

    def get_action(self, state):
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            dist, value = self.policy(state)
            action = dist.sample()
            log_prob = dist.log_prob(action)
            
        return action.cpu().numpy()[0], log_prob.cpu().numpy()[0], value.cpu().numpy()[0]

    def store_transition(self, transition):
        # Transition: (state, action, reward, next_state, val, log_prob, done)
        self.experience_buffer.append(transition)

    def learn(self):
        if len(self.experience_buffer) < PPO_BATCH_SIZE:
            return
            
        # Unpack Buffer
        # Fix UserWarning: creating tensor from list of arrays is slow
        # Convert to numpy array first
        states_arr = np.array([t[0] for t in self.experience_buffer], dtype=np.float32)
        states = torch.FloatTensor(states_arr).to(self.device)
        
        actions_arr = np.array([t[1] for t in self.experience_buffer], dtype=np.float32)
        actions = torch.FloatTensor(actions_arr).to(self.device)
        
        rewards = [t[2] for t in self.experience_buffer]
        
        next_states_arr = np.array([t[3] for t in self.experience_buffer], dtype=np.float32)
        next_states = torch.FloatTensor(next_states_arr).to(self.device)
        
        old_values_arr = np.array([t[4] for t in self.experience_buffer], dtype=np.float32)
        old_values = torch.FloatTensor(old_values_arr).to(self.device)
        
        old_log_probs_arr = np.array([t[5] for t in self.experience_buffer], dtype=np.float32)
        old_log_probs = torch.FloatTensor(old_log_probs_arr).to(self.device)
        
        dones = [t[6] for t in self.experience_buffer]
        
        # Compute Advantages (GAE)
        returns = []
        gae = 0
        with torch.no_grad():
            _, next_value = self.policy(next_states[-1].unsqueeze(0))
            next_value = next_value.item()
            
        for step in reversed(range(len(rewards))):
            if step == len(rewards) - 1:
                next_non_terminal = 1.0 - dones[step]
                next_val = next_value
            else:
                next_non_terminal = 1.0 - dones[step]
                next_val = old_values[step + 1].item()
                
            r = rewards[step]
            if isinstance(r, (np.ndarray, list)):
                r = float(np.sum(r))
            else:
                r = float(r)
                
            delta = r + PPO_GAMMA * next_val * next_non_terminal - old_values[step].item()
            gae = float(delta) + PPO_GAMMA * PPO_GAE_LAMBDA * next_non_terminal * float(gae)
            # Detach to convert to float/numpy before appending to list to avoid graph retention
            return_val = float(gae) + old_values[step].item()
            returns.insert(0, return_val)
        # Convert returns to numpy array first to avoid slow tensor creation and sequence errors
        returns_arr = np.array(returns, dtype=np.float32)
        returns = torch.FloatTensor(returns_arr).to(self.device)
        advantages = returns - old_values
        # Normalize Advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # PPO Update Loop
        for _ in range(PPO_EPOCHS):
            # Recalculate current probabilities and values
            dist, current_values = self.policy(states)
            current_log_probs = dist.log_prob(actions)
            
            # Ratio
            ratios = torch.exp(current_log_probs - old_log_probs)
            
            # Surrogate Loss
            surr1 = ratios * advantages.unsqueeze(1)
            surr2 = torch.clamp(ratios, 1 - PPO_CLIP_RATIO, 1 + PPO_CLIP_RATIO) * advantages.unsqueeze(1)
            
            actor_loss = -torch.min(surr1, surr2).mean()
            critic_loss = nn.MSELoss()(current_values.squeeze(), returns)
            
            entropy = dist.entropy().mean()
            
            loss = actor_loss + PPO_VALUE_COEF * critic_loss - PPO_ENTROPY_COEF * entropy
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
        # Clear Buffer
        self.experience_buffer = []

    def save(self, path):
        torch.save(self.policy.state_dict(), path)

    def load(self, path):
        checkpoint = torch.load(path, map_location=self.device)
        model_dict = self.policy.state_dict()
        
        # Handle shape mismatches for actor.0.weight and critic.0.weight dynamically
        for k in ['actor.0.weight', 'critic.0.weight']:
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

        # Update and load
        model_dict.update(checkpoint)
        self.policy.load_state_dict(model_dict, strict=False)
