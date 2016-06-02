#!/usr/bin/env python


def traverse_task_requires(task):
    """
    Parameters
    ----------
    task : luigi.Task instance

    Returns
    ------
    None : doesn't return anything

    Traverses the luigi.Task instance's requirements
    down the dependency graph and makes sure all
    get executed
    """
    if task.requires() is not None:
        traverse_task(task.requires())
        task.requires().run()
    return
