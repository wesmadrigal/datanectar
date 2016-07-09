#!/usr/bin/env python
import os
import sys
import time

import luigi

from pathutils import project_path
PROJECT_CODE_PATH = os.path.join(project_path(), 'code')
sys.path.append(PROJECT_CODE_PATH)

from util.nectar_s3_task import NectarS3Task
from util.nectar_local_task import NectarLocalTask

TheTaskClass = NectarLocalTask if os.getenv('ENV', 'local') == 'local' else NectarS3Task

class TestTask(TheTaskClass):
    def requires(self):
        return None

    def run(self):
        with self.output().open('w') as f:
            time.sleep(10)
            f.write("test successfully ran at {0}".format(time.time()))


class WithDependencyTask(TheTaskClass):
    aparam = luigi.Parameter()
    def requires(self):
        return TestTask()
    
    def run(self):
        with self.output().open('w') as f:
            time.sleep(120)
            f.write("{0} successfully ran at {1}".format(self.__class__.__name__, time.time()))


if __name__ == '__main__':
    luigi.run()
