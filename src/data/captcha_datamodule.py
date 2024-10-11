import datetime

from typing import Any, Dict, Optional, Tuple
import torch
import glob
import os
import numpy as np
from PIL import Image
from lightning import LightningDataModule
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision.transforms import ToTensor

from src.data.components.build_dataset import DataParser, CaptchaDataset, DataDownloader


class CaptchaDataModule(LightningDataModule):
    def __init__(
        self,
        dataset: dict[str, dict[str, str]] = {},
        batch_size: int = 64,
        num_workers: int = 0,
        pin_memory: bool = False,
        force_parse_data: bool = False,
    ) -> None:
        super().__init__()
        self.save_hyperparameters(logger=False)

        self.data_train: Optional[Dataset] = None
        self.data_val: Optional[Dataset] = None
        self.data_test: Optional[Dataset] = None
        self.force_parse_data = force_parse_data

    @property
    def num_classes(self) -> int:
        """Get the number of classes.

        :return: The number of MNIST classes (10).
        """
        return 36

    def prepare_data(self) -> None:
        """Download data if needed. Lightning ensures that `self.prepare_data()` is called only
        within a single process on CPU, so you can safely add your downloading logic within. In
        case of multi-node training, the execution of this hook depends upon
        `self.prepare_data_per_node()`.

        Do not use it to assign state (self.x = y).
        """
        # Download Datasets and place into the correct folders
        # os.makedirs(self.hparams.dataset.train.raw_data, exist_ok=True)
        # if not os.path.exists(self.hparams.dataset.train.raw_data) or self.force_parse_data:
        #     DataDownloader().get_dataset(
        #         "http://mai0313.com/share/Datasets/train.zip", self.hparams.dataset.train.raw_data
        #     )
        # if not os.path.exists(self.hparams.dataset.validation.raw_data) or self.force_parse_data:
        #     DataDownloader().get_dataset(
        #         "http://mai0313.com/share/Datasets/val.zip", self.hparams.dataset.validation.raw_data
        #     )
        # if not os.path.exists(self.hparams.dataset.test.raw_data) or self.force_parse_data:
        #     DataDownloader().get_dataset(
        #         "http://mai0313.com/share/Datasets/test.zip", self.hparams.dataset.test.raw_data
        #     )

        # Parse the data
        if not os.path.exists(self.hparams.dataset.train.parsed_data) or self.force_parse_data:
            DataParser().process_images(self.hparams.dataset.train.raw_data, self.hparams.dataset.train.parsed_data)
        if not os.path.exists(self.hparams.dataset.validation.parsed_data) or self.force_parse_data:
            DataParser().process_images(
                self.hparams.dataset.validation.raw_data, self.hparams.dataset.validation.parsed_data
            )
        if not os.path.exists(self.hparams.dataset.test.parsed_data) or self.force_parse_data:
            DataParser().process_images(self.hparams.dataset.test.raw_data, self.hparams.dataset.test.parsed_data)

    def setup(self, stage: Optional[str] = None):
        """Load data. Set variables: `self.data_train`, `self.data_val`, `self.data_test`.

        This method is called by Lightning before `trainer.fit()`, `trainer.validate()`, `trainer.test()`, and
        `trainer.predict()`, so be careful not to execute things like random split twice! Also, it is called after
        `self.prepare_data()` and there is a barrier in between which ensures that all the processes proceed to
        `self.setup()` once the data is prepared and available for use.

        :param stage: The stage to setup. Either `"fit"`, `"validate"`, `"test"`, or `"predict"`. Defaults to ``None``.
        """
        if self.trainer is not None:
            if self.hparams.batch_size % self.trainer.world_size != 0:
                raise RuntimeError(
                    f"Batch size ({self.hparams.batch_size}) is not divisible by the number of devices ({self.trainer.world_size})."
                )
            self.batch_size_per_device = self.hparams.batch_size // self.trainer.world_size

        # load and split datasets only if not loaded already
        self.hparams.train_dataset = self.hparams.dataset.train.parsed_data
        self.hparams.val_dataset = self.hparams.dataset.validation.parsed_data
        self.hparams.test_dataset = self.hparams.dataset.test.parsed_data

        if not self.data_train and not self.data_val and not self.data_test:
            self.data_train = CaptchaDataset(self.hparams.train_dataset)
            self.data_val = CaptchaDataset(self.hparams.val_dataset)
            self.data_test = CaptchaDataset(self.hparams.test_dataset)

    def train_dataloader(self) -> DataLoader[Any]:
        """Create and return the train dataloader.

        :return: The train dataloader.
        """
        return DataLoader(
            dataset=self.data_train,
            batch_size=self.hparams.batch_size,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            shuffle=True,
        )

    def val_dataloader(self) -> DataLoader[Any]:
        """Create and return the validation dataloader.

        :return: The validation dataloader.
        """
        return DataLoader(
            dataset=self.data_val,
            batch_size=self.hparams.batch_size,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            shuffle=False,
        )

    def test_dataloader(self) -> DataLoader[Any]:
        """Create and return the test dataloader.

        :return: The test dataloader.
        """
        return DataLoader(
            dataset=self.data_test,
            batch_size=self.hparams.batch_size,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            shuffle=False,
        )

    def teardown(self, stage: Optional[str] = None) -> None:
        """Lightning hook for cleaning up after `trainer.fit()`, `trainer.validate()`,
        `trainer.test()`, and `trainer.predict()`.

        :param stage: The stage being torn down. Either `"fit"`, `"validate"`, `"test"`, or `"predict"`.
            Defaults to ``None``.
        """
        pass

    def state_dict(self) -> Dict[Any, Any]:
        """Called when saving a checkpoint. Implement to generate and save the datamodule state.

        :return: A dictionary containing the datamodule state that you want to save.
        """
        return {}

    def load_state_dict(self, state_dict: Dict[str, Any]) -> None:
        """Called when loading a checkpoint. Implement to reload datamodule state given datamodule
        `state_dict()`.

        :param state_dict: The datamodule state returned by `self.state_dict()`.
        """
        pass
