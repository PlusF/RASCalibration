import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from calibrator import Calibrator
from utils import remove_cosmic_ray
from dataloader.DataLoader import find_skip, extract_keyword


class FileReader:
    def __init__(self):
        self.filename: str = ''
        self.time: str = ''
        self.integration: float = 0
        self.accumulation: int = 0
        self.interval: float = 0
        self.df: pd.DataFrame = pd.DataFrame()

        self.pos_arr: np.ndarray = None
        self.pos_arr_relative_accumulated: np.ndarray = None
        self.xdata: np.ndarray = None
        self.spectra: np.ndarray = None
        self.spectra_accumulated: np.ndarray = None

    def __str__(self):
        return f'filename: {self.filename}\n' \
               f'time: {self.time}\n' \
               f'integration: {self.integration}\n' \
               f'accumulation: {self.accumulation}\n' \
               f'interval: {self.interval}\n' \
               f'data:\n{self.df}' \


    def load(self, filename):
        self.filename = filename
        with open(filename, 'r') as f:
            lines = f.readlines()
        self.df = pd.read_csv(filename, skiprows=find_skip(lines) - 3, header=None, index_col=0)
        self.time = extract_keyword(lines, 'time')
        self.integration = float(extract_keyword(lines, 'integration'))
        self.accumulation = int(extract_keyword(lines, 'accumulation'))
        self.interval = float(extract_keyword(lines, 'interval'))

        self.pos_arr = self.df.loc['pos_x':'pos_z'].values.T
        self.xdata = self.df.index[3:].values.astype(float)
        self.spectra = self.df.iloc[3:].values.astype(float).T

    def accumulate(self):
        spectra_accumulated = np.empty([0, self.xdata.shape[0]])
        pos_arr_new = []

        tmp_accumulated = np.zeros(self.xdata.shape[0])
        pos_origin = self.pos_arr[0]
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
                pos_arr_new.append(pos_check - pos_origin)
                tmp_accumulated = np.zeros(self.xdata.shape[0])

        self.pos_arr_relative_accumulated = np.array(pos_arr_new)
        self.spectra_accumulated = spectra_accumulated


class RayleighCalibrator(Calibrator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.center: float = 630
        self.wavelength_range = 134
        self.reader_raw = FileReader()
        self.reader_bg = FileReader()
        self.reader_ref = FileReader()

        self.map_data: np.ndarray = None
        self.map_data_accumulated: np.ndarray = None
        self.bg_data: np.ndarray = None
        self.bg_data_accumulated: np.ndarray = None
        self.num_place: int = 0

        self.set_measurement('Rayleigh')

    def load_raw(self, filename):
        self.reader_raw.load(filename)
        self.reader_raw.accumulate()
        self.xdata = self.reader_raw.xdata.copy()
        self.map_data = self.reader_raw.spectra.copy()
        self.map_data_accumulated = self.reader_raw.spectra_accumulated.copy()
        self.num_place = self.reader_raw.spectra_accumulated.shape[0]

    def load_bg(self, filename):
        self.reader_bg.load(filename)
        self.reader_bg.accumulate()
        if self.xdata is None:
            self.xdata = self.reader_bg.xdata
        # remove cosmic ray automatically
        self.bg_data = remove_cosmic_ray(self.reader_bg.spectra.copy())
        self.bg_data_accumulated = remove_cosmic_ray(self.reader_bg.spectra_accumulated.copy())[0]

    def load_ref(self, filename):
        self.reader_ref.load(filename)
        spec_sum = self.reader_ref.spectra.sum(axis=0)
        self.set_data(self.reader_ref.xdata, spec_sum)

    def set_initial_xdata(self, center: float):
        self.center = center
        self.xdata = np.linspace(center - self.wavelength_range / 2, center + self.wavelength_range / 2, self.reader_ref.xdata.shape[0])

    def reset_map_data(self):
        if self.reader_raw.spectra is not None:
            # for cosmic ray removal and background correction
            self.map_data = self.reader_raw.spectra.copy()
            self.map_data_accumulated = self.reader_raw.spectra_accumulated.copy()

    def reset_ref_data(self):
        if self.reader_ref.spectra is not None:
            # for calibration
            spec_sum = self.reader_ref.spectra.sum(axis=0)
            self.set_data(self.reader_ref.xdata, spec_sum)

    def correct_background(self):
        if self.bg_data is None:
            raise ValueError('No background data.')
        self.map_data -= self.bg_data_accumulated / self.reader_bg.accumulation
        self.map_data_accumulated -= self.bg_data_accumulated

    def remove_cosmic_ray(self):
        self.map_data = remove_cosmic_ray(self.map_data)
        self.map_data_accumulated = remove_cosmic_ray(self.map_data_accumulated)

    def show_fit_result(self, ax: plt.Axes) -> None:
        ax.plot(self.xdata, self.ydata, color='k')
        ymin, ymax = ax.get_ylim()

        for i, (fitted_x, true_x) in enumerate(zip(self.fitted_x, self.found_x_true)):
            if i == 0:
                ax.vlines(fitted_x, ymin, ymax, color='r', linewidth=1, label='Found peak')
                ax.vlines(true_x, ymin, ymax, color='b', linewidth=1, label='True value')
            else:
                ax.vlines(fitted_x, ymin, ymax, color='r', linewidth=1)
                ax.vlines(true_x, ymin, ymax, color='b', linewidth=1)
        ax.legend()

    def imshow(self, ax: plt.Axes, color_range: list, cmap: str, ev=False) -> None:
        mesh = ax.pcolormesh(self.map_data_accumulated, cmap=cmap)
        mesh.set_clim(*color_range)

        xtick = np.arange(0, self.xdata.shape[0], 128)
        ax.set_xticks(xtick)
        label = self.xdata[xtick]
        if ev:
            label = 1240 / label
        ax.set_xticklabels(np.round(label))
        ax.set_yticks(range(self.map_data_accumulated.shape[0]))
        ax.set_yticklabels(map(lambda x: round(np.linalg.norm(x)), self.reader_raw.pos_arr_relative_accumulated))
