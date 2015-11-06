import os
import logging

import Tkinter

from tkFileDialog import askdirectory

from nrk_downloader import NRKDownloader


class NRKDownloaderApp(Tkinter.Tk):
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)

        self.minsize(width=800, height=100)
        self.option_add('*Font', 'arial 20')

        self.downloader = NRKDownloader()
        self.urls = []

        self.parent = parent

        self.path_label = Tkinter.Label(self, text=u'Output path')
        self.path_variable = Tkinter.StringVar()
        self.path_entry = Tkinter.Entry(self, textvariable=self.path_variable)
        self.path_button = Tkinter.Button(self, text=u'Browse', command=self.on_path_browse)

        self.extension_label = Tkinter.Label(self, text=u'Extension:')
        self.extension_variable = Tkinter.StringVar()
        self.extension_entry = Tkinter.OptionMenu(
            self, self.extension_variable, * self.downloader.file_extensions, command=self.on_extension_select
        )

        self.url_label = Tkinter.Label(self, text=u'Add URL')
        self.url_variable = Tkinter.StringVar()
        self.url_entry = Tkinter.Entry(self, textvariable=self.url_variable)
        self.url_button = Tkinter.Button(self, text=u'Add', command=self.on_url_add)

        self.url_list_label = Tkinter.Label(self, text=u'URLs')
        self.url_list_variable = Tkinter.Listbox(self, selectmode=Tkinter.EXTENDED)

        self.remove_selection_button = Tkinter.Button(self, text=u'Remove selected URLs', command=self.remove_urls)
        self.download_button = Tkinter.Button(self, text=u'Download', command=self.download)

        self.initialize()

    def create_grid(self):
        self.grid()
        self.grid_columnconfigure(0, weight=1)

    def download(self):
        for i in range(len(self.urls)):
            print self.urls[i]

            success = self.downloader.download(self.urls[i])

            color = 'green' if success else 'red'

            self.url_list_variable.itemconfig(i, bg=color)

    @staticmethod
    def reset_text_field(field):
        field.focus_set()
        field.selection_range(0, 0)

    def on_path_change(self):
        path = self.path_variable.get()

        if path:
            if os.path.isdir(path):
                self.downloader.path = self.downloader.parse_url(path)

                self.path_entry.config(background='green')

                self.path_variable.set(path)
            else:
                self.downloader.path = ''

                self.path_entry.config(background='red')
        else:
            self.path_entry.config(background='white')

        self.reset_text_field(self.path_entry)

    def on_path_browse(self):
        self.path_variable.set(askdirectory())

    def on_extension_select(self, extension=None):
        self.downloader.file_extension = self.extension_variable.get()

    def add_url(self, url):
        self.urls.append(url)

        self.url_list_variable.insert(Tkinter.END, url)

    def remove_urls(self):
        pass

    def get_url(self):
        url = self.url_variable.get()

        if url:
            return self.downloader.parse_url(url)
        else:
            return ''

    def on_url_set(self, event=None):
        url = self.get_url()

        if self.downloader.is_valid_url(url):
            if url not in self.urls:
                self.add_url(url)

                self.url_variable.set(u'')

            self.reset_text_field(self.url_entry)

    def on_url_change(self):
        url = self.get_url()

        if url:
            if self.downloader.is_valid_url(url):
                self.url_entry.config(background='green')
            else:
                self.url_entry.config(background='red')
        else:
            self.url_entry.config(background='white')

    def on_url_add(self):
        self.on_url_set()

    def create_path_variable(self):
        self.path_variable.trace('w', lambda name, index, mode, v=self.path_variable: self.on_path_change())

        self.path_label.grid(row=0, column=0, columnspan=2, sticky='W')
        self.path_entry.grid(row=1, column=0, sticky='EW')
        self.path_button.grid(row=1, column=1)

    def create_file_extension(self):
        self.extension_variable.set(self.downloader.file_extension)

        self.extension_entry.grid(row=1, column=2)

    def create_url_variable(self):
        self.url_variable.trace('w', lambda name, index, mode, v=self.url_variable: self.on_url_change())
        self.url_entry.bind('<Return>', self.on_url_set)

        self.url_label.grid(row=2, column=0, columnspan=2, sticky='W')
        self.url_entry.grid(row=3, column=0, columnspan=2, sticky='EW')
        self.url_button.grid(row=3, column=2)

    def create_url_list(self):
        self.url_list_label.grid(row=4, column=0, columnspan=2, sticky='W')
        self.url_list_variable.grid(row=5, column=0, columnspan=3, sticky='EW')

    def create_control_buttons(self):
        self.remove_selection_button.grid(row=6, column=0, sticky='W')
        self.download_button.grid(row=6, column=2)

    def initialize(self):
        self.create_grid()

        self.create_path_variable()
        self.create_file_extension()
        self.create_url_variable()
        self.create_url_list()
        self.create_control_buttons()

        self.resizable(True, True)

        self.update()


if __name__ == '__main__':
    app = NRKDownloaderApp(None)
    app.title('NRK Downloader')

    logging.basicConfig(level=logging.INFO)

    app.mainloop()
