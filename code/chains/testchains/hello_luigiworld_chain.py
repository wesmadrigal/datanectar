#!/usr/bin/env python
import os
import sys
import time

import luigi

from pathutils import project_path
PROJECT_CODE_PATH = os.path.join(project_path(), 'code')
sys.path.append(PROJECT_CODE_PATH)

from util.s3task import NectarS3Task

class TestS3Task(NectarS3Task):
    def requires(self):
        return None

    def output(self):
        if os.getenv('ENV', 'local') == 'local':
            return self.get_local_target()
        return luigi.s3.S3Target(
                self.get_s3target_path(),
                client=self.s3client
                )

    def run(self):
        with self.output().open('w') as f:
            time.sleep(120)
            f.write("test successfully ran at {0}".format(time.time()))

class WithDepTask(NectarS3Task):
    random_param = luigi.Parameter()
    def requires(self):
        return TestS3Task()
    
    def output(self):       
        if os.getenv('ENV', 'local') == 'local':
            return self.get_local_target()
        return luigi.s3.S3Target(
                self.get_s3target_path(),
                client=self.s3client
                )

    def run(self):
        with self.output().open('w') as f:
            f.write("WithDepTask successfully ran at {0}".format(time.time()))


if __name__ == '__main__':
    luigi.run()
