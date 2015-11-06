import os
import Tkinter

from tkFileDialog import askdirectory

from nrk_downloader import NRKDownloader


class NRKDownloaderApp(Tkinter.Tk):
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)

        self.downloader = NRKDownloader()
        self.urls = []

        self.parent = parent

        self.path_variable = None
        self.path_entry = None
        self.path_button = None

        self.extension_variable = None
        self.extension_entry = None

        self.url_variable = None
        self.url_entry = None
        self.url_button = None

        self.initialize()

    def create_grid(self):
        self.grid()
        self.grid_columnconfigure(0, weight=1)

    def on_path_set(self, event=None, path=None):
        if path is None:
            path = self.path_variable.get()

        if path:
            if os.path.isdir(path):
                self.downloader.path = path

                self.path_variable.set(path)

                self.path_entry.focus_set()
                self.path_entry.selection_range(0, Tkinter.END)
            else:
                self.path_variable.set(u"Please enter a valid path")

    def on_path_browse(self):
        self.on_path_set(path=askdirectory())

    def on_extension_select(self, extension=None):
        self.downloader.file_extension = self.extension_variable.get()

    def create_path_variable(self):
        self.path_variable = Tkinter.StringVar()
        self.path_variable.set(u"Output path")

        self.path_entry = Tkinter.Entry(self, textvariable=self.path_variable)
        self.path_entry.bind("<Return>", self.on_path_set)

        self.path_button = Tkinter.Button(self, text=u"Browse", command=self.on_path_browse)

        self.path_entry.grid(row=0, column=0)
        self.path_button.grid(row=0, column=1)

    def create_file_extension(self):
        self.extension_variable = Tkinter.StringVar()
        self.extension_variable.set(self.downloader.file_extension)

        self.extension_entry = Tkinter.OptionMenu(
            self, self.extension_variable, *self.downloader.file_extensions, command=self.on_extension_select
        )

        self.extension_entry.grid(row=0, column=2)

    def on_url_set(self, event=None):
        url = self.url_variable.get()

        if url:
            url = self.downloader.parse_url(url)

            if not self.downloader.is_valid_url(url):
                self.url_variable.set(u"Please enter a valid url")

                return

            if url not in self.urls:
                self.urls.append(url)

            self.url_variable.set(u"Add url")

            self.url_entry.focus_set()
            self.url_entry.selection_range(0, Tkinter.END)

        print(self.urls)

    def on_url_add(self):
        self.on_url_set()

    def create_url_variable(self):
        self.url_variable = Tkinter.StringVar()
        self.url_variable.set(u"Add url")

        self.url_entry = Tkinter.Entry(self, textvariable=self.url_variable)
        self.url_entry.bind("<Return>", self.on_url_set)

        self.url_button = Tkinter.Button(self, text=u"Add", command=self.on_url_add)

        self.url_entry.grid(row=1, column=0)
        self.url_button.grid(row=1, column=1)

    def initialize(self):
        self.create_grid()

        self.create_path_variable()
        self.create_file_extension()
        self.create_url_variable()

        self.resizable(True, True)

        self.update()
        self.geometry(self.geometry())


if __name__ == "__main__":
    app = NRKDownloaderApp(None)
    app.title('NRK Downloader')

    app.mainloop()
