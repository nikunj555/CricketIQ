import torch
import torch.nn as nn
from typing import Optional, Tuple

class BiLSTMBattingPhaseClassifier(nn.Module):
    """
    Bidirectional LSTM for temporal cricket batting action phase recognition.
    
    Inputs:
        x: FloatTensor of shape (batch_size, seq_len, input_dim) containing
           normalized kinematic pose features per frame.
        lengths: Optional LongTensor of valid sequence lengths.
        
    Outputs:
        logits: FloatTensor of shape (batch_size, seq_len, num_classes)
    """
    def __init__(
        self,
        input_dim: int = 14,
        hidden_dim: int = 64,
        num_layers: int = 2,
        num_classes: int = 7,
        dropout: float = 0.3
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes

        # Feature normalization projection
        self.input_norm = nn.LayerNorm(input_dim)
        self.fc_in = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

        # Bidirectional temporal LSTM
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0
        )

        # Output classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x: torch.Tensor, lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
        # x: (B, T, D)
        x_norm = self.input_norm(x)
        feat = self.fc_in(x_norm)
        
        if lengths is not None:
            packed = nn.utils.rnn.pack_padded_sequence(
                feat, lengths.cpu(), batch_first=True, enforce_sorted=False
            )
            lstm_out, _ = self.lstm(packed)
            lstm_out, _ = nn.utils.rnn.pad_packed_sequence(lstm_out, batch_first=True)
        else:
            lstm_out, _ = self.lstm(feat)

        logits = self.classifier(lstm_out)
        return logits
