import numpy as np
import pandas as pd
from dataloader.DataLoader import find_skip, extract_keyword


def remove_cosmic_ray_1d(spectrum: np.ndarray, width: int, threshold: float):
    spectrum = spectrum.copy()
    intensity = np.diff(spectrum)
    median_int = np.median(intensity)
    mad_int = np.median([np.abs(intensity - median_int)])
    if mad_int == 0:
        mad_int = 1e-4
    modified_scores = 0.6745 * (intensity - median_int) / mad_int
    spikes = abs(modified_scores) > threshold

    for i in np.arange(len(spikes)):
        if spikes[i]:
            w = np.arange(i - width, i + 1 + width)  # スパイク周りの2 m + 1個のデータを取り出す
            w = w[(0 <= w) & (w < (spectrum.shape[0] - 1))]  # 範囲を超えないようトリミング
            w2 = w[spikes[w] == False]  # スパイクでない値を抽出し，
            if len(w2) > 0:
                spectrum[i] = np.mean(spectrum[w2])  # 平均を計算し補完
    return spectrum


def remove_cosmic_ray(spectrum: np.ndarray, width: int = 3, threshold: float = 7):
    if len(spectrum.shape) == 1:
        return remove_cosmic_ray_1d(spectrum, width, threshold)

    if len(spectrum.shape) == 2:
        data_removed = []
        for spec in spectrum:
            data_removed.append(remove_cosmic_ray_1d(spec, width, threshold))
        return np.array(data_removed)


def smooth_1d(spectrum, width):
    num_front = width // 2
    num_back = width // 2 + 1 if width % 2 else width // 2
    arr_append_front = np.array([spectrum[:i+1].mean() for i in range(num_front)])
    arr_append_back = np.array([spectrum[::-1][:i+1].mean() for i in range(num_back)])
    spectrum_extended = np.hstack([arr_append_front, spectrum, arr_append_back])
    spectrum_smoothed = np.convolve(spectrum_extended, np.ones(width) / width, mode='same')
    return spectrum_smoothed[num_front:-num_back]


def smooth(spectrum, width):
    if len(spectrum.shape) == 1:
        return smooth_1d(spectrum, width)

    if len(spectrum.shape) == 2:
        spectrum_smoothed = []
        for s in spectrum:
            spectrum_smoothed.append(smooth_1d(s, width))
        return np.array(spectrum_smoothed)


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
        self.pos_arr_absolute_accumulated: np.ndarray = None
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

        self.accumulate()

    def accumulate(self):
        spectra_accumulated = np.empty([0, self.xdata.shape[0]])
        pos_arr_rel_acc = []
        pos_arr_abs_acc = []

        tmp_accumulated = np.zeros(self.xdata.shape[0])
        pos_origin = self.pos_arr[0]
        pos_check = self.pos_arr[0]

        for i, (pos, spec) in enumerate(zip(self.pos_arr, self.spectra)):
            if self.pos_arr[i].all() == np.zeros(3).all():  # なぜ起きた？
                print(f'Warning: skip dangerous data {i}')
                continue
            if i % self.accumulation == 0:
                pos_check = self.pos_arr[i]
            else:
                if pos.any() != pos_check.any():
                    print(f'{i}: {pos}, {pos_check}')
                    raise ValueError('Spectra were got at different positions.')
            tmp_accumulated += spec

            if i % self.accumulation == self.accumulation - 1:
                spectra_accumulated = np.append(spectra_accumulated, tmp_accumulated.reshape([1, self.xdata.shape[0]]), axis=0)
                pos_arr_rel_acc.append(pos_check - pos_origin)
                pos_arr_abs_acc.append(pos_check)
                tmp_accumulated = np.zeros(self.xdata.shape[0])

        self.pos_arr_relative_accumulated = np.array(pos_arr_rel_acc)
        self.pos_arr_absolute_accumulated = np.array(pos_arr_abs_acc)
        self.spectra_accumulated = spectra_accumulated


def concat(filenames, filename_to_save):
    fr = FileReader()

    fr_list = []
    for filename in filenames:
        fr_tmp = FileReader()
        fr_tmp.load(filename)
        fr_list.append(fr_tmp)
        # TODO: check if metadata matches

    fr.filename = ','.join(filenames)
    fr.integration = fr_list[0].integration
    fr.accumulation = fr_list[0].accumulation
    fr.interval = fr_list[0].interval

    fr.pos_arr = fr_list[0].pos_arr
    fr.pos_arr_relative_accumulated = fr_list[0].pos_arr_relative_accumulated
    fr.xdata = np.hstack([f.xdata for f in fr_list])
    fr.spectra = np.hstack([f.spectra for f in fr_list])
    fr.spectra_accumulated = np.hstack([f.spectra_accumulated for f in fr_list])

    pos_data = fr.pos_arr
    pos_data = np.vstack([np.array(['pos_x', 'pos_y', 'pos_z']), pos_data]).T.astype(str)

    xdata = np.array(fr.xdata)
    map_data = fr.spectra
    map_data = np.vstack([xdata, map_data]).T.astype(str)

    data = np.vstack([pos_data, map_data])

    with open(filename_to_save, 'w') as f:
        f.write(f'# abs_path_raw: {fr.filename}\n')
        f.write(f'# abs_path_bg: \n')
        f.write(f'# abs_path_ref: \n')
        f.write(f'# calibration: \n')
        f.write(f'# time: \n')
        f.write(f'# integration: {fr.integration}\n')
        f.write(f'# accumulation: {fr.accumulation}\n')
        f.write(f'# interval: {fr.interval}\n')
        for d in data:
            f.write(','.join(d) + '\n')


if __name__ == '__main__':
    concat(
        [r"G:\My Drive\kaneda\Data_M2\230511\scan_upperleft_500bc.txt",
         r"G:\My Drive\kaneda\Data_M2\230511\scan_upperleft_630bc.txt",
         r"G:\My Drive\kaneda\Data_M2\230511\scan_upperleft_760bc.txt"],
        r'G:\My Drive\kaneda\Data_M2\230511\scan_upperleft_500_630_760.txt')
