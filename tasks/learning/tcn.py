import torch
import torch.nn as nn
import torch.nn.functional as F

class Chomp1d(nn.Module):
    """
    裁剪模块，用于因果卷积，移除多余的填充
    """
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, :-self.chomp_size].contiguous()

class TemporalBlock(nn.Module):
    """
    残差模块，包含两个因果卷积层
    """
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super(TemporalBlock, self).__init__()
        self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size,
                               stride=stride, padding=padding, dilation=dilation)
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(dropout)

        self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size,
                               stride=stride, padding=padding, dilation=dilation)
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(dropout)

        self.net = nn.Sequential(
            self.conv1, self.chomp1, self.relu1, self.dropout1,
            self.conv2, self.chomp2, self.relu2, self.dropout2
        )
        self.downsample = nn.Conv1d(n_inputs, n_outputs, kernel_size=1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()

    def forward(self, x):
        out = self.net(x)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)

class TemporalConvNet(nn.Module):
    """
    完整的 TCN 模型，包含多层 TemporalBlock
    """
    def __init__(self, num_inputs, num_channels, kernel_size=2, dropout=0.2):
        super(TemporalConvNet, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i  # 每层的膨胀系数
            in_channels = num_inputs if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers.append(TemporalBlock(in_channels, out_channels, kernel_size, stride=1,
                                         dilation=dilation_size, padding=(kernel_size-1) * dilation_size,
                                         dropout=dropout))

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

# 示例：如何定义一个完整的 TCN 模型
if __name__ == "__main__":
    batch_size = 8
    seq_len = 50
    input_dim = 3  # 每个时间步的特征维度
    num_channels = [16, 32, 64]  # 每层的隐藏通道数
    kernel_size = 2
    dropout = 0.2

    model = TemporalConvNet(num_inputs=input_dim, num_channels=num_channels, kernel_size=kernel_size, dropout=dropout)
    print(model)

    # 输入 (Batch, Input Channels, Sequence Length)
    x = torch.randn(batch_size, input_dim, seq_len)

    # 输出 (Batch, Output Channels, Sequence Length)
    output = model(x)
    print("Output shape:", output.shape)
