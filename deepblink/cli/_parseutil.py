"""Utility file with custom argparse types / classes.

This utility file is used separate to avoid circular dependencies between
_parser.py and the individual _commands.py.
"""

from typing import Union
import argparse
import os
import re


class FileType:
    """Custom type for files with given extensions."""

    def __init__(self, extensions: Union[tuple, list]):
        self.extensions = extensions

    def __call__(self, value):  # noqa: D102
        if not os.path.isfile(value):
            raise argparse.ArgumentTypeError(
                f"Input must be a file. '{value}' does not."
            )

        if not any([value.endswith(e) for e in self.extensions]):
            raise argparse.ArgumentTypeError(
                f"Input file must have extension {self.extensions}. '{value}' does not."
            )
        return value


class FileFolderType:
    """Custom type supporting folders or files with given extensions."""

    def __init__(self, extensions: Union[tuple, list]):
        self.extensions = extensions

    def __call__(self, value):  # noqa: D102
        if not os.path.isdir(value):
            if not FileType(self.extensions)(value):
                raise argparse.ArgumentTypeError(
                    f"Input value must be file or folder. '{value}' is not."
                )
        return value


class FolderType:
    """Custom type supporting folders."""

    def __init__(self):
        pass

    def __call__(self, value):  # noqa: D102
        if not os.path.isdir(value):
            raise argparse.ArgumentTypeError(
                f"Input value must be folder and must exist. '{value}' is not."
            )
        return value


class ShapeType:
    """Custom type for image shapes."""

    def __init__(self):
        self.remove_characters = ["(", ")", " "]
        self.allowed_characters = "xy3ctz"
        self.required_characters = ["x", "y"]

    def __call__(self, value):  # noqa: D102
        if not isinstance(value, str):
            raise ValueError(f"Input value must be a string. '{value}' is not.")

        raw_value = value
        for c in self.remove_characters:
            value = value.replace(c, "")
        if not bool(re.match(f"^[{self.allowed_characters},]+$", value)):
            raise ValueError(
                f"Input must only contain values '{self.allowed_characters},'. '{raw_value}' does not."
            )
        if not bool(
            re.match(
                f"^([{self.allowed_characters}],)+[{self.allowed_characters}]$", value
            )
        ):
            raise ValueError(
                f"Input must have format '(?,?,?,?)'. '{raw_value}' does not."
            )
        if not all([c in value for c in self.required_characters]):
            raise ValueError(
                f"Input must contain {self.required_characters}. '{raw_value}' does not."
            )
        return raw_value


class CustomFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom changes to argparse's default help text formatter."""

    def add_usage(self, usage, actions, groups, prefix=None):
        """Helpformatter internal usage description function overwrite."""
        if prefix is None:
            prefix = "Usage: "
        return super(CustomFormatter, self).add_usage(usage, actions, groups, prefix)


# TODO find a simpler and safer solution
def _add_utils(parser: argparse.ArgumentParser):
    """A very hacky way of trying to move this group to the bottom of help text."""
    group = parser.add_argument_group("General utilities")
    group.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this message.",
    )
    group.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s 0.0.6",
        help="Show %(prog)s's version number.",
    )
    group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Set program output to verbose printing all important steps.",
    )
    group.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)