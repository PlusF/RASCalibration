import numpy as np
import matplotlib.pyplot as plt
from calibrator import Calibrator
from utils import remove_cosmic_ray, smooth, FileReader


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
        self.bg_data_accumulated_smoothed: np.ndarray = None
        self.num_pos: int = 0

        self.set_measurement('Rayleigh')

    def load_raw(self, filename):
        self.reader_raw.load(filename)
        self.xdata = self.reader_raw.xdata.copy()
        self.map_data = self.reader_raw.spectra.copy()
        self.map_data_accumulated = self.reader_raw.spectra_accumulated.copy()
        self.num_pos = self.reader_raw.spectra_accumulated.shape[0]

    def load_bg(self, filename):
        self.reader_bg.load(filename)
        if self.xdata is None:
            self.xdata = self.reader_bg.xdata
        # remove cosmic ray and smooth automatically
        self.bg_data_accumulated_smoothed = smooth(remove_cosmic_ray(self.reader_bg.spectra_accumulated), width=100)[0]

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
        if self.bg_data_accumulated_smoothed is None:
            raise ValueError('No background data.')
        self.map_data -= self.bg_data_accumulated_smoothed / self.reader_bg.accumulation
        self.map_data_accumulated -= self.bg_data_accumulated_smoothed

    def remove_cosmic_ray(self):
        self.map_data = remove_cosmic_ray(self.map_data)
        self.map_data_accumulated = remove_cosmic_ray(self.map_data_accumulated)

    def smooth(self):
        self.map_data = smooth(self.map_data, 100)
        self.map_data_accumulated = smooth(self.map_data_accumulated, 100)

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
