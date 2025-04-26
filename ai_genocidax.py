import torch
import torch.nn as nn
import torch.optim as optim
import os
import random

MODEL_PATH = "save/genocidax.pth"

class GenocidaxNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(19, 64),  # input size updated with more features
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 5)  # UP, DOWN, LEFT, RIGHT, SHOOT
        )

    def forward(self, x):
        return self.fc(x)

class GenocidaxAI:
    def __init__(self, epsilon=0.2):  # Higher epsilon to promote exploration
        self.model = GenocidaxNet()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.epsilon = epsilon
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.05

        if os.path.exists(MODEL_PATH):
            self.model.load_state_dict(torch.load(MODEL_PATH))
        else:
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    def save_model(self):
        torch.save(self.model.state_dict(), MODEL_PATH)

    def decide_action(self, player_pos, geno_pos, player_bullet, geno_bullet, obstacles):
        if random.random() < self.epsilon:
            # Priorité au mouvement vers le joueur
            return self.simple_chase_dir(player_pos, geno_pos) if random.random() < 0.5 else "SHOOT"

        obs_vec = [0] * 9
        offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        for idx, (dx, dy) in enumerate(offsets):
            ox, oy = geno_pos[0] + dx, geno_pos[1] + dy
            if (oy, ox) in obstacles:
                obs_vec[idx] = 1

        features = [
            player_pos[0], player_pos[1],
            geno_pos[0], geno_pos[1],
            player_pos[0] - geno_pos[0],
            player_pos[1] - geno_pos[1],
            *obs_vec,
        ]

        for bullet in (player_bullet, geno_bullet):
            if bullet:
                features.append(bullet[0] - geno_pos[0])
                features.append(bullet[1] - geno_pos[1])
            else:
                features.append(0.0)
                features.append(0.0)

        state = torch.tensor(features, dtype=torch.float32)

        if random.random() < self.epsilon:
            # Encourage bumping into player if close
            if abs(player_pos[0] - geno_pos[0]) + abs(player_pos[1] - geno_pos[1]) <= 3:
                dx = player_pos[0] - geno_pos[0]
                dy = player_pos[1] - geno_pos[1]
                if abs(dx) > abs(dy):
                    return 'RIGHT' if dx > 0 else 'LEFT'
                else:
                    return 'DOWN' if dy > 0 else 'UP'
            return random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT', 'SHOOT'])

        with torch.no_grad():
            output = self.model(state)
            action = torch.argmax(output).item()

        return ['UP', 'DOWN', 'LEFT', 'RIGHT', 'SHOOT'][action]
    
    def build_state_tensor(self, player_pos, geno_pos, player_bullet, geno_bullet, obstacles):
        obs_vec = [0] * 9
        offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        for idx, (dx, dy) in enumerate(offsets):
            ox, oy = geno_pos[0] + dx, geno_pos[1] + dy
            if (oy, ox) in obstacles:
                obs_vec[idx] = 1

        features = [
            player_pos[0], player_pos[1],
            geno_pos[0], geno_pos[1],
            player_pos[0] - geno_pos[0],
            player_pos[1] - geno_pos[1],
            *obs_vec,
        ]

        for bullet in (player_bullet, geno_bullet):
            if bullet:
                features.append(bullet[0] - geno_pos[0])
                features.append(bullet[1] - geno_pos[1])
            else:
                features.append(0.0)
                features.append(0.0)

        return torch.tensor(features, dtype=torch.float32)


    def train(self, memory):
        if len(memory) < 10:
            return

        states, actions, rewards = zip(*memory)
        states_tensor = torch.stack(states)
        actions_tensor = torch.tensor(actions, dtype=torch.long)
        rewards_tensor = torch.tensor(rewards, dtype=torch.float32)

        logits = self.model(states_tensor)
        log_probs = torch.log_softmax(logits, dim=1)
        selected_log_probs = log_probs[range(len(actions_tensor)), actions_tensor]

        loss = -(selected_log_probs * rewards_tensor).mean()

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Anneal epsilon over time to encourage exploitation
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    # Chase
    def simple_chase_dir(self, player_pos, geno_pos):   
        dx = player_pos[0] - geno_pos[0]
        dy = player_pos[1] - geno_pos[1]
        if abs(dx) > abs(dy):
            return "RIGHT" if dx > 0 else "LEFT"
        else:
            return "DOWN" if dy > 0 else "UP"