from diatom import *
import unittest
import io

class TestExpData(unittest.TestCase):

    def test_existing_exp_file(self):

        mdata = MoleculeData()
        self.assertRaises(
            SystemExit, mdata.set_exp_data, 'some_file', markers=[1]
        )

    def test_exp_data_shape(self):

        mdata = MoleculeData()
        exp_data_string = \
        """
        8
        1  0  2.5  0.000000000  1  5.0e-03    8  5
        2  0  3.5  27.92907799  1  2.554E-03  8  5
        3  0  4.5  63.82044637  1  2.589E-03  8  5
        4  0  5.5  107.6598777  1  2.993E-03  8  5
        5  0  6.5  159.4241657  1  3.105E-03  8  5
        6  0  7.5  219.0977590  1  3.052E-03  8  5
        7  0  8.5  286.6573545  1  3.059E-03  8  5
        8  0  9.5  362.0793175  1  3.108E-03  8  5
        """

        data_stream = io.StringIO(exp_data_string)
        mdata.set_exp_data(data_stream, markers=[1])
        print(mdata.exp_data)

        self.assertEqual(
            mdata.exp_data.shape[0], 8
        )