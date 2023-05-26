import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.backend_bases
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler
from RayleighCalibrator import RayleighCalibrator


class MainWindow(tk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.master = master
        if os.name == 'nt':
            self.width_master = 1800
            self.height_master = 1000
        else:
            self.width_master = 1350
            self.height_master = 600
        self.master.geometry(f'{self.width_master}x{self.height_master}')

        self.calibrator = RayleighCalibrator()

        # スペクトルの線．Auto ScaleをOffにした際にスケールを保つため，スペクトルを更新する際は線のみ削除する
        self.line = []

        # フォルダ選択ダイアログを開く際のデフォルトディレクトリ
        self.folder = './'

        self.create_widgets()

    def create_widgets(self) -> None:
        # canvas
        if os.name == 'nt':
            self.width_canvas = 1450
            self.height_canvas = 950
            dpi = 75
        else:
            self.width_canvas = 475
            self.height_canvas = 275
            dpi = 50
        fig, self.ax = plt.subplots(1, 2, figsize=(self.width_canvas / dpi, self.height_canvas / dpi), dpi=dpi)
        self.canvas = FigureCanvasTkAgg(fig, self.master)
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=3)
        toolbar = NavigationToolbar2Tk(self.canvas, self.master, pack_toolbar=False)
        toolbar.update()
        toolbar.grid(row=3, column=0)
        plt.subplots_adjust(left=0.05, right=0.99, bottom=0.05, top=0.99)
        fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('key_press_event', self.key_pressed)
        self.canvas.mpl_connect('key_press_event', key_press_handler)

        # frames
        # ある程度のウィジェットをひとまとまりにするためのフレーム群
        frame_data = tk.LabelFrame(self.master, text='Data')
        frame_selected = tk.LabelFrame(self.master, text='Selected')
        frame_download = tk.LabelFrame(self.master, text='Download')
        frame_plot = tk.LabelFrame(self.master, text='Plot')
        frame_data.grid(row=0, column=1, columnspan=2)
        frame_selected.grid(row=1, column=1, columnspan=2)
        frame_download.grid(row=2, column=1)
        frame_plot.grid(row=2, column=2)

        # frame_data
        # inputしたデータやキャリブレーションの設定，background correctionやcosmic ray removalの設定もできる
        label_raw = tk.Label(frame_data, text='Raw:')
        self.filename_raw = tk.StringVar(value='please drag & drop!')
        label_filename_raw = tk.Label(frame_data, textvariable=self.filename_raw)
        label_bg = tk.Label(frame_data, text='Background:')
        label_bg.bind('<Button-1>', self.show_bg)
        self.filename_bg = tk.StringVar(value='please drag & drop!')
        label_filename_bg = tk.Label(frame_data, textvariable=self.filename_bg)
        label_filename_bg.bind('<Button-1>', self.show_bg)
        label_ref = tk.Label(frame_data, text='Reference:')
        label_ref.bind('<Button-1>', self.show_ref)
        self.filename_ref = tk.StringVar(value='please drag & drop!')
        label_filename_ref = tk.Label(frame_data, textvariable=self.filename_ref)
        label_filename_ref.bind('<Button-1>', self.show_ref)
        label_center = tk.Label(frame_data, text='Center [nm]:')
        self.center = tk.DoubleVar(value=self.calibrator.center)
        combobox_center = ttk.Combobox(frame_data, textvariable=self.center, values=[500, 630, 760], width=7, justify=tk.CENTER)
        self.material = tk.StringVar(value=self.calibrator.get_material_list()[0])
        optionmenu_material = tk.OptionMenu(frame_data, self.material, *self.calibrator.get_material_list())
        self.dimension = tk.StringVar(value=self.calibrator.get_dimension_list()[0])
        optionmenu_dimension = tk.OptionMenu(frame_data, self.dimension, *self.calibrator.get_dimension_list())
        self.function = tk.StringVar(value=self.calibrator.get_function_list()[0])
        self.optionmenu_function = tk.OptionMenu(frame_data, self.function, *self.calibrator.get_function_list())
        self.optionmenu_function.config(state=tk.DISABLED)
        self.easy = tk.BooleanVar(value=True)
        checkbutton_easy = tk.Checkbutton(frame_data, text='easy', variable=self.easy, command=self.switch_easy)
        self.do_background_correction = tk.BooleanVar(value=False)
        self.checkbutton_bg = tk.Checkbutton(frame_data, text='BG', variable=self.do_background_correction, command=self.reload, state=tk.DISABLED)
        self.cosmic_ray_removal = tk.BooleanVar(value=False)
        self.checkbutton_crr = tk.Checkbutton(frame_data, text='CRR', variable=self.cosmic_ray_removal, command=self.reload, state=tk.DISABLED)
        self.smoothing = tk.BooleanVar(value=False)
        self.checkbutton_sm = tk.Checkbutton(frame_data, text='Smooth', variable=self.smoothing, command=self.reload, state=tk.DISABLED)
        self.button_calibrate = tk.Button(frame_data, text='CALIBRATE', command=self.calibrate, state=tk.DISABLED)

        label_raw.grid(row=0, column=0)
        label_filename_raw.grid(row=0, column=1, columnspan=2)
        label_bg.grid(row=1, column=0)
        label_filename_bg.grid(row=1, column=1, columnspan=2)
        label_ref.grid(row=2, column=0)
        label_filename_ref.grid(row=2, column=1, columnspan=2)
        label_center.grid(row=3, column=0)
        combobox_center.grid(row=3, column=1, columnspan=2)
        optionmenu_material.grid(row=4, column=0)
        optionmenu_dimension.grid(row=4, column=1)
        self.optionmenu_function.grid(row=4, column=2)
        checkbutton_easy.grid(row=4, column=3)
        self.checkbutton_bg.grid(row=5, column=0)
        self.checkbutton_crr.grid(row=5, column=1)
        self.checkbutton_sm.grid(row=5, column=2)
        self.button_calibrate.grid(row=5, column=3)

        # frame_selected
        # 表示中のスペクトルの情報を表示
        # TODO: 現時点はインデックスと座標だけだが，測定条件の細かい情報も表示したい
        label_index = tk.Label(frame_selected, text='  index  ')
        label_pos_x = tk.Label(frame_selected, text='  pos_x  ')
        label_pos_y = tk.Label(frame_selected, text='  pos_y  ')
        label_pos_z = tk.Label(frame_selected, text='  pos_z  ')
        self.index_to_show = tk.IntVar(value=0)
        label_index_value = tk.Label(frame_selected, textvariable=self.index_to_show)
        self.pos_x = tk.DoubleVar(value=0)
        label_pos_x_value = tk.Label(frame_selected, textvariable=self.pos_x)
        self.pos_y = tk.DoubleVar(value=0)
        label_pos_y_value = tk.Label(frame_selected, textvariable=self.pos_y)
        self.pos_z = tk.DoubleVar(value=0)
        label_pos_z_value = tk.Label(frame_selected, textvariable=self.pos_z)

        label_index.grid(row=0, column=0)
        label_pos_x.grid(row=0, column=1)
        label_pos_y.grid(row=0, column=2)
        label_pos_z.grid(row=0, column=3)
        label_index_value.grid(row=1, column=0)
        label_pos_x_value.grid(row=1, column=1)
        label_pos_y_value.grid(row=1, column=2)
        label_pos_z_value.grid(row=1, column=3)

        # frame_download
        # ダウンロード関連のウェジェット
        self.file_to_download = tk.Variable(value=[])
        self.listbox = tk.Listbox(frame_download, listvariable=self.file_to_download, selectmode=tk.EXTENDED, width=8,
                                  height=10, justify=tk.CENTER)
        self.listbox.bind('<Button-2>', self.delete)
        self.listbox.bind('<Button-3>', self.delete)
        scrollbar = tk.Scrollbar(frame_download)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)
        self.button_add = tk.Button(frame_download, text='ADD', command=self.add, width=8)
        self.button_add_all = tk.Button(frame_download, text='ADD ALL', command=self.add_all, width=8)
        self.button_delete = tk.Button(frame_download, text='DELETE', command=self.delete, width=8)
        self.button_delete_all = tk.Button(frame_download, text='DELETE ALL', command=self.delete_all, width=8)
        self.button_save_each = tk.Button(frame_download, text='SAVE EACH', command=self.save_each, width=8)
        self.button_save_map = tk.Button(frame_download, text='SAVE MAP', command=self.save_map, width=8)

        self.listbox.grid(row=0, column=0, rowspan=6)
        scrollbar.grid(row=0, column=1, rowspan=6)
        self.button_add.grid(row=0, column=2)
        self.button_add_all.grid(row=1, column=2)
        self.button_delete.grid(row=2, column=2)
        self.button_delete_all.grid(row=3, column=2)
        self.button_save_each.grid(row=4, column=2)
        self.button_save_map.grid(row=5, column=2)

        # frame plot
        # マッピングのカラーバーの設定．最小値最大値に加え，マッピングのカラーマップも設定できる．X軸をeV表記にしたり，AutoScaleのOn/Offも
        self.color_range_1 = tk.DoubleVar(value=0)
        self.color_range_2 = tk.DoubleVar(value=2000)
        entry_color_range_1 = tk.Entry(frame_plot, textvariable=self.color_range_1, width=7, justify=tk.CENTER)
        entry_color_range_2 = tk.Entry(frame_plot, textvariable=self.color_range_2, width=7, justify=tk.CENTER)
        self.map_color = tk.StringVar(value='hot')
        self.optionmenu_map_color = tk.OptionMenu(frame_plot, self.map_color,
                                                  *sorted(['viridis', 'plasma', 'inferno', 'magma', 'cividis',
                                                           'Wistia', 'hot', 'binary', 'bone', 'cool', 'copper',
                                                           'gray', 'pink', 'spring', 'summer', 'autumn', 'winter',
                                                           'RdBu', 'Spectral', 'bwr', 'coolwarm', 'hsv', 'twilight',
                                                           'CMRmap', 'cubehelix', 'brg', 'gist_rainbow', 'rainbow',
                                                           'jet', 'nipy_spectral', 'gist_ncar']),
                                                  command=self.imshow)
        self.optionmenu_map_color.config(state=tk.DISABLED)
        self.ev = tk.BooleanVar(value=False)
        self.checkbox_ev = tk.Checkbutton(frame_plot, text='eV', variable=self.ev, command=self.switch_ev, state=tk.DISABLED)
        self.autoscale = tk.BooleanVar(value=True)
        checkbox_autoscale = tk.Checkbutton(frame_plot, text='Auto Scale', variable=self.autoscale)
        self.button_apply = tk.Button(frame_plot, text='APPLY', command=self.imshow, width=7, state=tk.DISABLED)

        entry_color_range_1.grid(row=0, column=0)
        entry_color_range_2.grid(row=0, column=1)
        self.button_apply.grid(row=1, column=0, columnspan=2)
        self.optionmenu_map_color.grid(row=2, column=0, columnspan=2)
        self.checkbox_ev.grid(row=3, column=0)
        checkbox_autoscale.grid(row=3, column=1)

        # canvas_drop
        # ファイルをドラッグ&ドロップする際のガイド用のウィジェット．基本は非表示．
        self.canvas_drop = tk.Canvas(self.master, width=self.width_master, height=self.height_master)
        self.canvas_drop.create_rectangle(0, 0, self.width_master, self.height_master / 3, fill='white')
        self.canvas_drop.create_rectangle(0, self.height_master / 3, self.width_master, self.height_master * 2 / 3, fill='lightgray')
        self.canvas_drop.create_rectangle(0, self.height_master * 2 / 3, self.width_master, self.height_master, fill='gray')
        self.canvas_drop.create_text(self.width_master / 2, self.height_master / 6, text='2D Map RAS File',
                                     font=('Arial', 30))
        self.canvas_drop.create_text(self.width_master / 2, self.height_master / 2, text='Background File',
                                     font=('Arial', 30))
        self.canvas_drop.create_text(self.width_master / 2, self.height_master * 5 / 6, text='Reference RAS File',
                                     font=('Arial', 30))

    def switch_easy(self):
        # キャリブレーション用ピーク検出の際，単に最大値抽出するか，関数でピークフィットするかの設定．
        # easyがonの時は最大値抽出
        if self.easy.get():
            self.optionmenu_function.config(state=tk.DISABLED)
        else:
            self.optionmenu_function.config(state=tk.ACTIVE)

    def switch_ev(self):
        # X軸を波長にするかエネルギーにするか
        if self.ev.get():
            if self.calibrator.xdata[0] == 0:
                messagebox.showerror(title='Error', message='Data contains zero.')
                self.ev.set(False)
        self.reload()

    def calibrate(self) -> None:
        self.calibrator.reset_ref_data()
        self.calibrator.set_initial_xdata(self.center.get())
        self.calibrator.set_dimension(int(self.dimension.get()[0]))
        self.calibrator.set_material(self.material.get())
        self.calibrator.set_function(self.function.get())
        self.calibrator.set_search_width(5)
        ok = self.calibrator.calibrate(easy=self.easy.get())
        if not ok:
            messagebox.showerror('Error', 'Peaks not found.')
            return
        self.ax[1].cla()
        self.calibrator.show_fit_result(self.ax[1])
        self.canvas.draw()

        self.line = []
        self.imshow()  # to update the xticklabels

    def reload(self):
        # background correctionやcosmic ray removalの設定，ファイルの読み込み時にグラフを更新するための関数
        # 二重にbackground correctionやcosmic ray removalをかけないよう，まず生データをセットする
        self.calibrator.reset_map_data()
        if self.do_background_correction.get():
            if self.calibrator.reader_bg.filename == '':
                messagebox.showerror(title='Error', message='No background data.')
                return
            self.calibrator.correct_background()
        if self.cosmic_ray_removal.get():
            self.calibrator.remove_cosmic_ray()
        if self.smoothing.get():
            self.calibrator.smooth()
        self.imshow()
        self.update_plot()

    def on_click(self, event: matplotlib.backend_bases.MouseEvent) -> None:
        # マップをクリックして表示するスペクトルを選択
        if event.ydata is None:
            return
        # 右側のプロットには反応させない
        if os.name == 'nt' and event.x > self.width_canvas / 2:
            return
        if os.name == 'posix' and event.x > self.width_canvas:
            return
        self.index_to_show.set(int(np.floor(event.ydata)))
        self.update_position_info()
        self.update_plot()

    def key_pressed(self, event: matplotlib.backend_bases.KeyEvent) -> None:
        # キーボード入力イベントを処理
        if event.key == 'enter':
            self.reload()
            return
        # 上下ボタンを押したら表示するスペクトルを変更
        index_selected = self.index_to_show.get()
        if event.key == 'up' and index_selected < self.calibrator.data_length - 1:
            self.index_to_show.set(index_selected + 1)
        elif event.key == 'down' and 0 < index_selected:
            self.index_to_show.set(index_selected - 1)
        else:
            return
        # 座標情報を表示
        self.update_position_info()
        self.update_plot()

    def update_position_info(self):
        x, y, z = map(
            lambda p: round(p, 1),
            self.calibrator.reader_raw.pos_arr_absolute_accumulated[self.index_to_show.get()])
        self.pos_x.set(x)
        self.pos_y.set(y)
        self.pos_z.set(z)

    def imshow(self, event=None) -> None:
        # マップを表示
        if self.calibrator.map_data is None:
            return
        self.ax[0].cla()
        # 表示中のスペクトルを点線で挟んで示してあげる
        self.horizontal_line_1 = self.ax[0].axhline(color='w', lw=1.5, ls='--')
        self.horizontal_line_1.set_visible(True)
        self.horizontal_line_2 = self.ax[0].axhline(color='w', lw=1.5, ls='--')
        self.horizontal_line_2.set_visible(True)
        self.calibrator.imshow(self.ax[0], [self.color_range_1.get(), self.color_range_2.get()], self.map_color.get(), ev=self.ev.get())
        self.canvas.draw()

    def update_plot(self) -> None:
        index_to_show = self.index_to_show.get()
        # 範囲外のインデックスの場合は表示を更新しない
        if not (0 <= index_to_show < self.calibrator.data_length):
            return
        self.horizontal_line_1.set_ydata(index_to_show)
        self.horizontal_line_2.set_ydata(index_to_show + 1)

        # AutoScale関係の設定
        if self.autoscale.get():
            plt.autoscale(True)
            self.ax[1].cla()
        else:
            if self.line:
                plt.autoscale(False)  # The very first time requires autoscale
                self.line[0].remove()
            else:  # for after calibration
                self.ax[1].cla()

        x = self.calibrator.xdata.copy()
        if self.ev.get():
            x = 1240 / x
        self.line = self.ax[1].plot(
            x,
            self.calibrator.map_data_accumulated[index_to_show],
            label=f'{index_to_show} ({self.pos_x.get()}, {self.pos_y.get()}, {self.pos_z.get()})', color='r', linewidth=0.8)
        self.ax[1].legend()
        self.canvas.draw()

    def show_bg(self, event=None):
        if self.calibrator.reader_bg.filename == '':
            return
        plt.autoscale(True)
        if self.line:
            self.line[0].remove()
        else:
            self.ax[1].cla()

        x = self.calibrator.xdata.copy()
        if self.ev.get():
            x = 1240 / x
        self.line = self.ax[1].plot(
            x,
            self.calibrator.bg_data_accumulated_smoothed,
            label='background', color='k', linewidth=0.8)

        self.canvas.draw()

    def show_ref(self, event=None):
        if self.calibrator.reader_ref.filename == '':
            return
        plt.autoscale(True)
        if self.line:
            self.line[0].remove()
        else:
            self.ax[1].cla()

        x = self.calibrator.xdata.copy()
        if self.ev.get():
            x = 1240 / x
        self.line = self.ax[1].plot(
            x,
            self.calibrator.ydata,
            label='reference', color='k', linewidth=0.8)

        self.canvas.draw()

    def drop(self, event: TkinterDnD.DnDEvent=None) -> None:
        # drag & dropのイベント処理
        self.canvas_drop.place_forget()

        # フォルダによってファイル名の情報のフォーマットが異なることがある
        if event.data[0] == '{':
            filename = event.data.split('} {')[0].strip('{').strip('}')
        else:
            filename = event.data.split()[0]

        # 何のデータかを，dropした位置から算出
        master_geometry = list(map(int, self.master.winfo_geometry().split('+')[1:]))
        dropped_place = (event.y_root - master_geometry[1] - 30) / self.height_canvas

        threshold = 1 / 3
        # OSによって違うものを修正
        if os.name == 'posix':
            threshold *= 2

        if dropped_place < threshold:  # raw data
            self.calibrator.load_raw(filename)
            self.filename_raw.set(os.path.basename(filename))
            self.folder = os.path.dirname(filename)
            self.checkbutton_crr.config(state=tk.ACTIVE)
            self.checkbutton_sm.config(state=tk.ACTIVE)

            self.optionmenu_map_color.config(state=tk.ACTIVE)
            self.button_apply.config(state=tk.ACTIVE)
            self.checkbox_ev.config(state=tk.ACTIVE)
            self.color_range_1.set(round(self.calibrator.map_data_accumulated.min()))
            self.color_range_2.set(round(self.calibrator.map_data_accumulated.max()))

            self.reset_when_drop_raw()
            self.reload()
            self.imshow()
            self.update_plot()
        elif dropped_place < threshold * 2:  # background data
            self.calibrator.load_bg(filename)
            self.filename_bg.set(os.path.basename(filename))
            self.checkbutton_bg.config(state=tk.ACTIVE)

            self.ax[1].cla()
            self.ax[1].plot(self.calibrator.xdata, self.calibrator.bg_data_accumulated_smoothed, color='k', label='background')
            self.canvas.draw()

            if self.calibrator.reader_raw.filename != '':
                self.imshow()
        else:  # reference data
            self.calibrator.load_ref(filename)
            self.filename_ref.set(os.path.split(filename)[-1])
            for material in self.calibrator.get_material_list():
                if material in filename:
                    self.material.set(material)
            for center in ['500', '630', '760']:
                if center in filename:
                    self.center.set(float(center))
            self.button_calibrate.config(state=tk.ACTIVE)

            self.ax[1].cla()
            self.ax[1].plot(self.calibrator.xdata, self.calibrator.ydata, color='k', label='reference')
            self.canvas.draw()

    def drop_enter(self, event: TkinterDnD.DnDEvent) -> None:
        # ドラッグしてウィンドウに入ってきた時，ガイド用のウィジェットを表示する
        self.canvas_drop.place(anchor='nw', x=0, y=0)

    def drop_leave(self, event: TkinterDnD.DnDEvent) -> None:
        # 離れたらウィジェットを非表示に
        self.canvas_drop.place_forget()

    def reset_when_drop_raw(self):
        self.do_background_correction.set(False)
        self.cosmic_ray_removal.set(False)
        self.smoothing.set(False)
        self.ev.set(False)
        self.delete_all()

    def add(self) -> None:
        # 保存したいスペクトルを追加
        # ここではインデックスを追加し，SAVE EACHボタンが押されたらインデックスに基づいてデータが保存される
        indices = self.file_to_download.get()
        if indices == '':
            indices = []
        else:
            indices = list(indices)

        # 既に存在する場合は追加しない
        if self.index_to_show.get() in indices:
            return
        indices.append(self.index_to_show.get())
        self.file_to_download.set(indices)

    def add_all(self) -> None:
        # すべてのインデックスをダウンロードリストに追加
        all_indices = list(range(self.calibrator.data_length))
        self.file_to_download.set(all_indices)

    def delete(self, event=None) -> None:
        # 保存予定のものを削除
        if not messagebox.askyesno('Confirmation', 'Delete these?'):
            return
        for idx in sorted(list(self.listbox.curselection()), reverse=True):
            self.listbox.delete(idx)

    def delete_all(self) -> None:
        # すべて削除
        for _ in range(len(self.file_to_download.get())):
            self.listbox.delete(0)

    def write_header(self, f):
        # スペクトルのデータを書き出す際，ファイルの最初のほうにメタデータを追加
        abs_path_raw = self.calibrator.reader_raw.filename
        abs_path_bg = self.calibrator.reader_bg.filename if self.do_background_correction.get() else ''
        abs_path_ref = self.calibrator.reader_ref.filename
        f.write(f'# abs_path_raw: {abs_path_raw}\n')
        f.write(f'# abs_path_bg: {abs_path_bg}\n')
        f.write(f'# abs_path_ref: {abs_path_ref}\n')
        f.write(f'# calibration: {self.calibrator.calibration_info}\n')
        f.write(f'# time: {self.calibrator.reader_raw.time}\n')
        f.write(f'# integration: {self.calibrator.reader_raw.integration}\n')
        f.write(f'# accumulation: {self.calibrator.reader_raw.accumulation}\n')
        f.write(f'# interval: {self.calibrator.reader_raw.interval}\n')
        f.write(f'# num_pos: {self.calibrator.reader_raw.num_pos}\n')

    def save_each(self) -> None:
        # インデックスごとに保存する
        if not self.file_to_download.get():
            messagebox.showinfo('Info', 'No file selected.')
            return

        folder_to_save = filedialog.askdirectory(initialdir=self.folder)
        if not folder_to_save:
            return

        for index in self.file_to_download.get():
            i1 = index * self.calibrator.reader_raw.accumulation
            i2 = (index + 1) * self.calibrator.reader_raw.accumulation
            map_data = np.vstack([self.calibrator.xdata, self.calibrator.map_data[i1:i2]]).T.astype(str)
            pos_data = np.vstack([np.array(['pos_x', 'pos_y', 'pos_z']), self.calibrator.reader_raw.pos_arr[i1:i2]]).T.astype(str)

            data = np.vstack([pos_data, map_data])

            filename = os.path.join(folder_to_save, f'{index}.txt')
            with open(filename, 'w') as f:
                self.write_header(f)
                for d in data:
                    f.write(','.join(d) + '\n')

    def save_map(self) -> None:
        if self.calibrator.reader_raw.filename == '':
            messagebox.showinfo('Info', 'No file.')
            return

        # マップデータとして保存
        filename = filedialog.asksaveasfilename(initialdir=self.folder)
        if not filename:
            return

        pos_data = self.calibrator.reader_raw.pos_arr
        pos_data = np.vstack([np.array(['pos_x', 'pos_y', 'pos_z']), pos_data]).T.astype(str)

        xdata = np.array(self.calibrator.xdata)
        map_data = self.calibrator.map_data
        map_data = np.vstack([xdata, map_data]).T.astype(str)

        data = np.vstack([pos_data, map_data])

        with open(filename, 'w') as f:
            self.write_header(f)
            for d in data:
                f.write(','.join(d) + '\n')

    def quit(self) -> None:
        self.master.quit()
        self.master.destroy()


def main():
    root = TkinterDnD.Tk()
    app = MainWindow(master=root)
    root.protocol('WM_DELETE_WINDOW', app.quit)
    root.drop_target_register(DND_FILES)
    root.dnd_bind('<<DropEnter>>', app.drop_enter)
    root.dnd_bind('<<DropLeave>>', app.drop_leave)
    root.dnd_bind('<<Drop>>', app.drop)
    app.mainloop()


if __name__ == '__main__':
    main()
