
import torch
import torch.nn as nn
import torch.optim as optim
import torch.backends.cudnn as cudnn
import numpy as np
import os

# TorchVision and data augmentation
import torchvision
import torchvision.transforms as transforms


# Models
from ViT import ViT
from Swin import SwinTransformer

# Data
from getdata import getData
from getdata import getAugmentation


# Some important parameters

# Image params
img_size = 128 # resize to this image size (square)
img_channels=3 # number of image channels

# Training params
bs = 32 # batch size
epochs = 500 # total training epochs
rand_aug = True # use random augmentation
load_check = False # to load a checkpoint

# For Transformers 
patch_size= 4 # patch size (square)
d_model=96 # dimensionality transformer representation


# ViT
N=10# Number of transformers blocks
heads=16 # Number of transformer block heads 

### For SWin

# D = 96 192 384 768
num_heads=[4, 6, 8, 12] # D/H = 24, 32, 48, 64
depths=[2, 4, 6, 6]
window_size=4


# computing device
device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Data augmentation
transform_train,transform_test=getAugmentation(img_size,rand_aug)

# Dataset and loaders
dataset="FOOD101"
trainset,trainloader,testset,testloader,num_classes=getData(dataset, bs, transform_train, transform_test)

## Model
'''
net=ViT(img_size, 
        img_channels, 
        patch_size, 
        d_model,
        N, 
        heads, 
        num_classes)
'''

net=SwinTransformer(img_size=img_size, 
                    patch_size=patch_size,
                    in_chans=img_channels, 
                    window_size=window_size, 
                    embed_dim=d_model, 
                    num_classes=num_classes,
                    num_heads=num_heads,
                    depths=depths)
net.to(device)

best_acc = 0.0
if load_check:
    print('==> Resuming from checkpoint..')
    assert os.path.isdir('checkpoint'), 'Error: no checkpoint directory found!'
    checkpoint = torch.load('./checkpoint/vit-ckpt.t7')
    net.load_state_dict(checkpoint['model_state_dict'])
    best_acc = checkpoint['acc']


# Loss is CE
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(net.parameters(), lr=0.00005)

if load_check:
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

# use ReduceOnPlateau or CosineAnnealing
#scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=5)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs, eta_min=1e-5)

##### Training
def train():
    
    net.train()
    train_loss = 0
    correct = 0
    total = 0
    for batch_idx, (inputs, targets) in enumerate(trainloader):
        inputs, targets = inputs.to(device), targets.to(device)
        
        outputs = net(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

        print('\r %d %d -- Loss: %.3f | Acc: %.2f%%' % (batch_idx+1, len(trainloader), train_loss/(batch_idx+1), 100.*correct/total), end="")

    return train_loss/(batch_idx+1),100.*correct/total

##### Validation
def test():
    global best_acc
    net.eval()
    test_loss = 0
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(testloader):
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net(inputs)
            loss = criterion(outputs, targets)

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            
            print('\r %d %d -- Loss: %.3f | Acc: %.2f%%' % (batch_idx+1, len(testloader), test_loss/(batch_idx+1), 100.*correct/total), end="")

    # Save checkpoint.
    acc = 100.*correct/total
    if acc > best_acc:
        print("")
        print('Saving checkpoint..')
        if not os.path.isdir('checkpoint'):
            os.mkdir('checkpoint')
        torch.save({
            'model_state_dict': net.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': test_loss,
            'acc': acc}, './checkpoint/vit-ckpt.t7')
        best_acc = acc

    return test_loss/(batch_idx+1),100.*correct/total
            

for epoch in range(epochs):
    print('\n============ Epoch: %d ==============' % epoch)
    print()

    print("Training, lr= %f" %(optimizer.param_groups[0]['lr']))
    trainloss,acc = train()
    print("")

    print("Validation, best acc=%f" %(best_acc))
    val_loss, acc = test()
    print("")

    #scheduler.step(trainloss) # step scheduling
    scheduler.step() # step scheduling
    
    
 
