import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from calibrator import Calibrator


class FileReader:
    def __init__(self):
        self.filename: str = ''
        self.time: str = ''
        self.integration: float = 0
        self.accumulation: int = 0
        self.interval: float = 0
        self.df: pd.DataFrame = pd.DataFrame()

        self.pos_arr: np.ndarray = None
        self.xdata: np.ndarray = None
        self.spectra: np.ndarray = None

    def __str__(self):
        return f'filename: {self.filename}\n' \
               f'time: {self.time}\n' \
               f'integration: {self.integration}\n' \
               f'accumulation: {self.accumulation}\n' \
               f'interval: {self.interval}\n' \
               f'data:\n{self.df}' \

    def load(self, filename):
        self.filename = filename
        self.df = pd.read_csv(filename, skiprows=4, header=None, index_col=0)
        with open(filename, 'r') as f:
            lines = f.readlines()
        self.time = lines[0].split(': ')[-1].strip('\n')
        self.integration = float(lines[1].split(': ')[-1])
        self.accumulation = float(lines[2].split(': ')[-1])
        self.interval = float(lines[3].split(': ')[-1])

        self.pos_arr = self.df.loc['pos_x':'pos_z'].values.T
        self.xdata = self.df.index[3:].values.astype(float)
        self.spectra = self.df.loc['0':].values.T

    def accumulate(self):
        spectra_accumulated = np.empty([0, self.xdata.shape[0]])
        pos_arr_new = []

        tmp_accumulated = np.zeros(self.xdata.shape[0])
        pos_check = self.pos_arr[0]

        for i, (pos, spec) in enumerate(zip(self.pos_arr, self.spectra)):
            if i % self.accumulation == 0:
                pos_check = self.pos_arr[i]
            else:
                if pos.any() != pos_check.any():
                    print(f'{i}: {pos}, {pos_check}')
                    raise ValueError('Spectra were got at different positions.')
            tmp_accumulated += spec

            if i % self.accumulation == self.accumulation - 1:
                spectra_accumulated = np.append(spectra_accumulated, tmp_accumulated.reshape([1, self.xdata.shape[0]]), axis=0)
                pos_arr_new.append(pos_check)
                tmp_accumulated = np.zeros(self.xdata.shape[0])

        self.pos_arr = np.array(pos_arr_new)
        self.spectra = spectra_accumulated


class RayleighCalibrator(Calibrator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.center: float = 630
        self.wavelength_range = 134
        self.reader_raw = FileReader()
        self.reader_ref = FileReader()

        self.map_data: np.ndarray = None
        self.num_place: int = 0

        self.set_measurement('Rayleigh')

    def load_raw(self, filename):
        self.reader_raw.load(filename)
        self.reader_raw.accumulate()
        self.xdata = self.reader_raw.xdata.copy()
        self.map_data = self.reader_raw.spectra
        self.num_place = self.reader_raw.spectra.shape[0]

    def load_ref(self, filename):
        self.reader_ref.load(filename)
        spec_sum = self.reader_ref.spectra.sum(axis=0)
        self.set_data(self.reader_ref.xdata, spec_sum)

    def set_initial_xdata(self, center: float):
        self.center = center
        self.xdata = np.linspace(center - self.wavelength_range / 2, center + self.wavelength_range / 2, self.reader_ref.xdata.shape[0])

    def reset_data(self):
        if self.reader_raw is None or self.reader_ref is None:
            raise ValueError('Load data before reset.')
        spec_sum = self.reader_ref.spectra.sum(axis=0)
        self.set_data(self.reader_ref.xdata, spec_sum)

    def show_fit_result(self, ax: plt.Axes) -> None:
        ax.plot(self.xdata, self.ydata, color='k')
        ymin, ymax = ax.get_ylim()

        for fitted_x in self.fitted_x:
            ax.vlines(fitted_x, ymin, ymax, color='r', linewidth=1)

    def imshow(self, ax: plt.Axes, color_range: list, cmap: str) -> None:
        mesh = ax.pcolormesh(self.map_data, cmap=cmap)
        mesh.set_clim(*color_range)

        xtick = np.arange(0, 1024, 128)
        ax.set_xticks(xtick)
        ax.set_xticklabels(map(round, self.xdata[xtick]))
        ax.set_yticks(range(self.reader_raw.spectra.shape[0]))
        ax.set_yticklabels(map(lambda x: round(np.linalg.norm(x)), self.reader_raw.pos_arr))


def test():
    filename_ref = '/Users/kanedaryoutarou/Desktop/1d.txt'
    filename_raw = '/Users/kanedaryoutarou/Desktop/2d.txt'

    rc = RayleighCalibrator()
    rc.load_raw(filename_raw)
    rc.load_ref(filename_ref)

    print(rc.reader_raw)
    print(rc.reader_raw.pos_arr)
    print(rc.reader_raw.xdata.shape)
    print(rc.reader_raw.spectra.shape)
    print(rc.reader_ref)


if __name__ == '__main__':
    test()
