"""Utility functions used by benchmarking scripts."""
from typing import Callable, List, Tuple
import argparse
import datetime
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import skimage.measure

import deepblink as pink


class NpzFileType:
    """Argparse type for .npz datasets."""

    def __call__(self, value):
        if not os.path.isfile(value) and not value.split(".")[-1] == "npz":
            print(os.path.isfile(value))
            print(value.split(".")[-1])
            raise argparse.ArgumentTypeError(
                f"Dataset must be of type npz. {value} is not."
            )
        return value


class FolderType:
    """Argparse type for folders only."""

    def __call__(self, value):
        if not os.path.isdir(value):
            raise argparse.ArgumentTypeError(
                f"Input must be of type directory. {value} is not."
            )
        return value


def _parse_args(test: bool = False):
    """Argument parser for benchmarks with models."""
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "-d", "--dataset", type=str, required=True, help="",
    )
    parser.add_argument(
        "-o", "--output", type=str, required=True, help="",
    )
    if test:
        parser.add_argument(
            "-m", "--model", type=str, required=True, help="",
        )
    args = parser.parse_args()
    return args


def _parse_args_fiji(test: bool = False):
    """Argument parser for benchmarks with file directories."""
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-b", "--basedir", type=str, required=True, help="")
    if test:
        parser.add_argument("-t", "--threshold", type=float, required=True, help="")
    args = parser.parse_args()
    return args


def get_coordinates(mask: np.ndarray) -> np.ndarray:
    """Segmentation mask -> coordinate list."""
    binary = np.round(mask.squeeze())
    label = skimage.measure.label(binary)
    props = skimage.measure.regionprops(label)
    coords = np.array([p.centroid for p in props])
    return coords


def row_col_offset(true_r: float, true_c: float, pred_r: float, pred_c: float) -> tuple:
    """Return raw offset between true and pred for both directions."""
    return (true_r - pred_r, true_c - pred_c)


def offset_euclidean(offset: List[tuple]) -> np.ndarray:
    """Calculates the euclidean distance based on row_column_offsets per coordinate."""
    return np.sqrt(np.sum(np.square(np.array(offset)), axis=-1))


def plot_metrics(fname: str, df: pd.DataFrame) -> None:
    """Plot F1 scores and prediction distributions."""
    _, ax = plt.subplots(2, 2, figsize=(20, 20))

    # F1 vs. cutoff line
    ax[0, 0].set_title("F1 score vs. cutoff")
    sns.lineplot("cutoff", "f1_score", data=df, ax=ax[0, 0])
    ax[0, 0].set_ylim(0, 1)

    # F1 histogram
    ax[0, 1].set_title("F1 score vs. cutoff")
    sns.distplot(df["f1_integral"], ax=ax[0, 1])
    ax[0, 1].set_xlim(0, 1)

    # Euclidean histogram
    ax[1, 0].set_title("Euclidean mean")
    sns.lineplot("cutoff", "mean_euclidean", data=df, ax=ax[1, 0])

    # Offset scatter
    try:
        flat_list = np.array(
            [item for sublist in df["offset"].to_numpy() for item in sublist]
        )
    except TypeError:
        flat_list = np.zeros((0, 0))

    ax[1, 1].set_title("Prediction offset")
    if flat_list.size > 0:
        sns.kdeplot(data=flat_list.T[0], data2=flat_list.T[1], ax=ax[1, 1])
    ax[1, 1].set_ylim(-3, 3)
    ax[1, 1].set_xlim(-3, 3)

    plt.savefig(fname)
    plt.close()


def print_scores(df: pd.DataFrame) -> None:
    """Print calculated metrics."""
    p = 4
    f1i_mean = df["f1_integral"].mean().round(p)
    f1i_std = df["f1_integral"].std().round(p)
    rmse_mean = df["mean_euclidean"].mean().round(p)
    rmse_std = df["mean_euclidean"].std().round(p)

    print(
        "Metrics on test set:\n"
        f"* F1 integral score: {f1i_mean} ± {f1i_std}\n"
        f"* Mean euclidean distance: {rmse_mean} ± {rmse_std}"
    )


def run_test(
    benchmark: str,
    dataset: str,
    output: str,
    fname_model: str,
    img_size: int,
    model_loader: Callable,
    normalize_fn: Callable,
    coordinate_loader: Callable,
) -> Tuple[float, ...]:
    """Testing loop for all tensorflow-model based benchmarks.

    Args:
        benchmark: Name of benchmark to create equally named folder.
        dataset: Path to npz file containing test data.
        output: Path to output directory in which "benchmark/" will be created.
        fname_model: Path to .h5 model file.
        img_size: Default image size for fixed-sized models.
        model_loader: Function that returns a tf.keras.models.Model. Using the inputs
            fname_model and img_size.
        normalize_fn: Function that normalizes a single input image. Dimensionality
            addition is not required!
        coordinate_loader: Function that maps on model output returning a list of
            coordinates with shape (n, 2).

    Returns:
        Mean f1_integral and mean_euclidean values as well as two saved files:
            * "benchmark/dataset/metrics/name.csv": File with all metric measurements
                at every cutoff.
            * "benchmark/dataset/metrics/name.pdf": Four plots for visual inspection.
                F1 vs. cutoff, f1_integral distribution, mean_euclidean distribution,
                coordinate prediction distribution relative to ground truth at 0, 0.
    """
    # Create output names
    today = datetime.date.today().strftime("%Y%m%d")
    bname_dataset = pink.io.basename(dataset)
    bname_file = f"test_{bname_dataset}_{today}"
    bname_output = os.path.join(output, benchmark, bname_dataset)

    os.makedirs(os.path.join(bname_output, "metrics"), exist_ok=True)
    fname_metrics = os.path.join(bname_output, "metrics", f"{bname_file}.csv")
    fname_plots = os.path.join(bname_output, "metrics", f"{bname_file}.pdf")

    # Verbose output
    print(f"Starting evaluation of {bname_file}.")

    # Import data from prepared dataset
    x_test, y_test = pink.io.load_npz(dataset, test_only=True)

    # Convert images
    test_imgs = np.array([normalize_fn(x) for x in x_test])
    test_imgs = np.expand_dims(test_imgs, 3)

    # Get model and import
    model = model_loader(fname_model, img_size)

    # Prediction
    pred_output = model.predict(test_imgs, batch_size=4)
    pred_coords = list(map(coordinate_loader, pred_output))

    # Calculate metrics and save to file
    df = pd.DataFrame()
    for i, (pred, true) in enumerate(zip(pred_coords, y_test)):
        curr_df = pink.metrics.compute_metrics(pred, true)
        curr_df["image"] = i
        df = df.append(curr_df)
    df.to_csv(fname_metrics)

    plot_metrics(fname_plots, df)

    print_scores(df)
