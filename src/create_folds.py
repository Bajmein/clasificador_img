# import time
import pandas as pd
import numpy as np
import os
import torch
from PIL import Image
from imblearn.over_sampling import SMOTE
from torch.utils.data import DataLoader, TensorDataset
from torchvision import transforms


def create_dataset(folder_path):
    my_list = []
    for category in ['NORMAL', 'PNEUMONIA']:
        category_path = os.path.join(folder_path, category)
        for file_name in os.listdir(category_path):
            file_path = os.path.join(category_path, file_name)
            if os.path.isfile(file_path) and file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                my_list.append([file_path, category])
    return pd.DataFrame(my_list, columns=['file_path', 'label'])


def label_dataset():
    import os
    dataset_dir = '../clasificador_img/input/'
    train_dir = os.path.join(dataset_dir, 'train/')
    val_dir = os.path.join(dataset_dir, 'val/')
    test_dir = os.path.join(dataset_dir, 'test/')
    print(f"Train directory: {train_dir}")

    try:
        train_df = create_dataset(train_dir)
        val_df = create_dataset(val_dir)
        test_df = create_dataset(test_dir)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Error: One or more directories are missing: {e}")

    if train_df.empty or val_df.empty or test_df.empty:
        raise ValueError("One or more datasets are empty. Please check the folder structure and data.")

    label_mapping = {'NORMAL': 0, 'PNEUMONIA': 1}
    train_df['label'] = train_df['label'].map(label_mapping)
    val_df['label'] = val_df['label'].map(label_mapping)
    test_df['label'] = test_df['label'].map(label_mapping)

    for dataset_name, df in zip(['Train', 'Validation', 'Test'], [train_df, val_df, test_df]):
        if df['label'].isnull().any():
            print(f"Warning: Unmapped labels found in {dataset_name} dataset.")
            print(df[df['label'].isnull()])
            raise ValueError(f"Unmapped labels in {dataset_name} dataset. Check folder names or label mapping.")

    return train_df, val_df, test_df


class ImageDataset(torch.utils.data.Dataset):
    def __init__(self, dataframe, transform=None):
        self.dataframe = dataframe
        self.transform = transform

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        img_path = self.dataframe.iloc[idx, 0]
        label = int(self.dataframe.iloc[idx, 1])
        img = Image.open(img_path).convert('L')

        if self.transform:
            img = self.transform(img)

        label = torch.tensor(int(label), dtype=torch.long)

        return img, label


def return_dataset():
    train_df, val_df, test_df = label_dataset()  # Asumiendo que tienes esta función definida

    # Transformaciones para el conjunto de entrenamiento (Data Augmentation)
    train_transform_cnn = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.Grayscale(),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.RandomAffine(degrees=10, translate=(0.1, 0.1)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5], std=[0.5]),
    ])

    # Transformaciones para los conjuntos de validación y test (sin aumento de datos)
    val_transform_cnn = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.Grayscale(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5], std=[0.5]),
    ])

    # Definir los datasets
    train_dataset_cnn = ImageDataset(train_df, transform=train_transform_cnn)
    val_dataset_cnn = ImageDataset(val_df, transform=val_transform_cnn)
    test_dataset_cnn = ImageDataset(test_df, transform=val_transform_cnn)

    # Aplicar SMOTE en los datos de entrenamiento
    smote = SMOTE(sampling_strategy='auto', random_state=42)
    data, labels = zip(*[(x.view(-1).numpy(), y.item()) for x, y in train_dataset_cnn])
    data, labels = np.array(data), np.array(labels)

    # Generar datos sintéticos
    data_resampled, labels_resampled = smote.fit_resample(data, labels)
    data_resampled = data_resampled.reshape(-1, 1, 256, 256)  # Ajustar dimensiones

    # Crear un TensorDataset con los datos balanceados
    smote_dataset = TensorDataset(torch.tensor(data_resampled, dtype=torch.float32),
                                  torch.tensor(labels_resampled, dtype=torch.long))

    batch_size = 32

    # Crear los DataLoaders
    train_loader_cnn = DataLoader(smote_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
    val_loader_cnn = DataLoader(val_dataset_cnn, batch_size=batch_size, shuffle=False, num_workers=4)
    test_loader_cnn = DataLoader(test_dataset_cnn, batch_size=batch_size, shuffle=False, num_workers=4)

    return train_loader_cnn, val_loader_cnn, test_loader_cnn


if __name__ == "__main__":
    return_dataset()
