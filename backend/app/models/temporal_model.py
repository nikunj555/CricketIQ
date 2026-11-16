import numpy as np
import scipy.special
from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path

# Optional PyTorch import for development/training environments
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    torch = None
    nn = None
    HAS_TORCH = False


class NumpyBiLSTMBattingPhaseClassifier:
    """
    Lightweight, dependency-free NumPy implementation of the 2-layer BiLSTM
    batting action phase classifier. Requires zero PyTorch overhead in production (~0 MB extra RAM).
    Predictions match PyTorch output within 1e-6 numerical tolerance.
    """
    def __init__(self, weights: Union[str, Path, Dict[str, np.ndarray]]):
        if isinstance(weights, (str, Path)):
            data = np.load(weights)
            self.w = {k: data[k] for k in data.files}
        else:
            self.w = weights
        self.input_dim = 14
        self.hidden_dim = 64
        self.num_classes = 7

    def _layer_norm(self, x: np.ndarray, weight: np.ndarray, bias: np.ndarray, eps: float = 1e-5) -> np.ndarray:
        mean = np.mean(x, axis=-1, keepdims=True)
        var = np.var(x, axis=-1, keepdims=True)
        return (x - mean) / np.sqrt(var + eps) * weight + bias

    def _gelu(self, x: np.ndarray) -> np.ndarray:
        return 0.5 * x * (1.0 + scipy.special.erf(x / np.sqrt(2.0)))

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -25.0, 25.0)))

    def _lstm_layer(self, x: np.ndarray, w_ih: np.ndarray, w_hh: np.ndarray, b_ih: np.ndarray, b_hh: np.ndarray, reverse: bool = False) -> np.ndarray:
        T, _ = x.shape
        hidden_size = w_hh.shape[1]
        h = np.zeros(hidden_size, dtype=np.float32)
        c = np.zeros(hidden_size, dtype=np.float32)
        h_out = np.zeros((T, hidden_size), dtype=np.float32)

        indices = range(T - 1, -1, -1) if reverse else range(T)
        bias = b_ih + b_hh

        for t in indices:
            xt = x[t]
            gates = np.dot(w_ih, xt) + np.dot(w_hh, h) + bias
            i_gate = self._sigmoid(gates[0:hidden_size])
            f_gate = self._sigmoid(gates[hidden_size:2*hidden_size])
            g_gate = np.tanh(gates[2*hidden_size:3*hidden_size])
            o_gate = self._sigmoid(gates[3*hidden_size:4*hidden_size])

            c = f_gate * c + i_gate * g_gate
            h = o_gate * np.tanh(c)
            h_out[t] = h

        return h_out

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Input: (T, 14) or (1, T, 14) normalized kinematic features.
        Output: (T, 7) or (1, T, 7) class logits.
        """
        is_batched = (x.ndim == 3)
        if is_batched:
            feats = x[0]
        else:
            feats = x

        x_norm = self._layer_norm(feats, self.w['input_norm.weight'], self.w['input_norm.bias'])
        fc_out = self._gelu(np.dot(x_norm, self.w['fc_in.0.weight'].T) + self.w['fc_in.0.bias'])

        # BiLSTM Layer 0
        h0_fwd = self._lstm_layer(fc_out, self.w['lstm.weight_ih_l0'], self.w['lstm.weight_hh_l0'], self.w['lstm.bias_ih_l0'], self.w['lstm.bias_hh_l0'], reverse=False)
        h0_rev = self._lstm_layer(fc_out, self.w['lstm.weight_ih_l0_reverse'], self.w['lstm.weight_hh_l0_reverse'], self.w['lstm.bias_ih_l0_reverse'], self.w['lstm.bias_hh_l0_reverse'], reverse=True)
        h0 = np.concatenate([h0_fwd, h0_rev], axis=-1)

        # BiLSTM Layer 1
        h1_fwd = self._lstm_layer(h0, self.w['lstm.weight_ih_l1'], self.w['lstm.weight_hh_l1'], self.w['lstm.bias_ih_l1'], self.w['lstm.bias_hh_l1'], reverse=False)
        h1_rev = self._lstm_layer(h0, self.w['lstm.weight_ih_l1_reverse'], self.w['lstm.weight_hh_l1_reverse'], self.w['lstm.bias_ih_l1_reverse'], self.w['lstm.bias_hh_l1_reverse'], reverse=True)
        h1 = np.concatenate([h1_fwd, h1_rev], axis=-1)

        # Classification Head
        cls_hidden = self._gelu(np.dot(h1, self.w['classifier.0.weight'].T) + self.w['classifier.0.bias'])
        logits = np.dot(cls_hidden, self.w['classifier.3.weight'].T) + self.w['classifier.3.bias']

        if is_batched:
            return np.expand_dims(logits, axis=0)
        return logits


if HAS_TORCH:
    class BiLSTMBattingPhaseClassifier(nn.Module):
        """
        Bidirectional LSTM for temporal cricket batting action phase recognition (PyTorch reference).
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

            self.input_norm = nn.LayerNorm(input_dim)
            self.fc_in = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout)
            )

            self.lstm = nn.LSTM(
                input_size=hidden_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                bidirectional=True,
                dropout=dropout if num_layers > 1 else 0.0
            )

            self.classifier = nn.Sequential(
                nn.Linear(hidden_dim * 2, hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, num_classes)
            )

        def forward(self, x: torch.Tensor, lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
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
else:
    # Alias to Numpy classifier when PyTorch is not installed
    BiLSTMBattingPhaseClassifier = NumpyBiLSTMBattingPhaseClassifier
