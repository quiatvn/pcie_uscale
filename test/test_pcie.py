# This file is Copyright (c) 2019-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import unittest
import os

class TestExamples(unittest.TestCase):
    def target_test(self, target):
        os.system("rm -rf examples/build")
        os.system("cd examples && python3 {}.py".format(target))
        self.assertEqual(os.path.isfile("examples/build/gateware/{}.v".format(target)), True)
        self.assertEqual(os.path.isfile("examples/build/csr.h"), True)
        self.assertEqual(os.path.isfile("examples/build/soc.h"), True)
        self.assertEqual(os.path.isfile("examples/build/mem.h"), True)

    def test_kc705_target(self):
        #self.target_test("kc705")
        self.target_test("kcu105")

    def gen_test(self, name):
        os.system("rm -rf examples/build")
        os.system("cd examples && python3 ../litepcie/gen.py {}.yml".format(name))
        errors = not os.path.isfile("examples/build/gateware/litepcie_core.v")
        os.system("rm -rf examples/build")
        return errors

    def test_ac702_gen(self):
        errors = self.gen_test("ac702")
        self.assertEqual(errors, 0)
