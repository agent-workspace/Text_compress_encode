"""
TextCompressor GUI - Tkinter interface for compression and archive operations.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import List, Optional
import threading

from archiver import create_archive, list_archive, preview_file, extract_from_archive, extract_all


class TextCompressorGUI:
    """Main GUI application for TextCompressor."""

    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("TextCompressor - ._t_ Archive Tool")
        self.root.geometry("900x700")

        # State
        self.selected_files: List[Path] = []
        self.current_archive: Optional[Path] = None
        self.archive_files: List[dict] = []
        self.last_directory = Path.home()

        # Create GUI
        self._create_widgets()
        self._update_button_states()

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # === FILE SELECTION PANEL ===
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="5")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(1, weight=1)

        # File listbox with scrollbar
        listbox_frame = ttk.Frame(file_frame)
        listbox_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)

        self.file_listbox = tk.Listbox(listbox_frame, height=8, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        # File selection buttons
        self.add_files_btn = ttk.Button(file_frame, text="Add Files", command=self._add_files)
        self.add_files_btn.grid(row=1, column=0, padx=(0, 5), sticky=tk.W)

        self.add_directory_btn = ttk.Button(file_frame, text="Add Directory", command=self._add_directory)
        self.add_directory_btn.grid(row=1, column=1, padx=5)

        self.remove_files_btn = ttk.Button(file_frame, text="Remove Selected", command=self._remove_selected)
        self.remove_files_btn.grid(row=1, column=2, padx=5)

        self.clear_files_btn = ttk.Button(file_frame, text="Clear All", command=self._clear_all)
        self.clear_files_btn.grid(row=1, column=3, padx=(5, 0), sticky=tk.E)

        # === OPERATION PANEL ===
        op_frame = ttk.LabelFrame(main_frame, text="Operations", padding="5")
        op_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        op_frame.columnconfigure(1, weight=1)

        self.compress_btn = ttk.Button(op_frame, text="Compress to Archive", command=self._compress_to_archive)
        self.compress_btn.grid(row=0, column=0, padx=(0, 10), pady=5, sticky=tk.W)

        self.extract_archive_btn = ttk.Button(op_frame, text="Extract Archive", command=self._extract_archive_dialog)
        self.extract_archive_btn.grid(row=0, column=1, pady=5)

        # Compression ratio display
        self.ratio_label = ttk.Label(op_frame, text="Compression ratio: --")
        self.ratio_label.grid(row=1, column=0, columnspan=2, pady=(5, 0))

        # === ARCHIVE BROWSER PANEL ===
        browser_frame = ttk.LabelFrame(main_frame, text="Archive Browser", padding="5")
        browser_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        browser_frame.columnconfigure(0, weight=1)
        browser_frame.rowconfigure(1, weight=1)
        browser_frame.rowconfigure(3, weight=2)
        main_frame.rowconfigure(2, weight=1)

        # Browse button
        self.browse_archive_btn = ttk.Button(browser_frame, text="Browse Archive", command=self._browse_archive)
        self.browse_archive_btn.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Archive file listbox
        archive_listbox_frame = ttk.Frame(browser_frame)
        archive_listbox_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        archive_listbox_frame.columnconfigure(0, weight=1)
        archive_listbox_frame.rowconfigure(0, weight=1)

        self.archive_listbox = tk.Listbox(archive_listbox_frame, height=6)
        self.archive_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.archive_listbox.bind('<<ListboxSelect>>', lambda e: self._update_button_states())

        archive_scrollbar = ttk.Scrollbar(archive_listbox_frame, orient=tk.VERTICAL, command=self.archive_listbox.yview)
        archive_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.archive_listbox.configure(yscrollcommand=archive_scrollbar.set)

        # Archive operation buttons
        button_frame = ttk.Frame(browser_frame)
        button_frame.grid(row=2, column=0, pady=(0, 5))

        self.preview_btn = ttk.Button(button_frame, text="Preview Selected", command=self._preview_selected)
        self.preview_btn.grid(row=0, column=0, padx=(0, 5))

        self.extract_selected_btn = ttk.Button(button_frame, text="Extract Selected", command=self._extract_selected)
        self.extract_selected_btn.grid(row=0, column=1, padx=5)

        self.extract_all_btn = ttk.Button(button_frame, text="Extract All", command=self._extract_all)
        self.extract_all_btn.grid(row=0, column=2, padx=(5, 0))

        # Preview text widget
        preview_frame = ttk.LabelFrame(browser_frame, text="Preview", padding="5")
        preview_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=10, state=tk.DISABLED, wrap=tk.WORD)
        self.preview_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # === STATUS BAR ===
        self.status_label = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=3, column=0, sticky=(tk.W, tk.E))

    def _update_button_states(self):
        """Enable/disable buttons based on current state."""
        # File selection buttons
        has_files = len(self.selected_files) > 0
        has_selection = len(self.file_listbox.curselection()) > 0

        self.compress_btn.config(state=tk.NORMAL if has_files else tk.DISABLED)
        self.remove_files_btn.config(state=tk.NORMAL if has_selection else tk.DISABLED)
        self.clear_files_btn.config(state=tk.NORMAL if has_files else tk.DISABLED)

        # Archive browser buttons
        has_archive = self.current_archive is not None
        has_archive_selection = len(self.archive_listbox.curselection()) > 0

        self.preview_btn.config(state=tk.NORMAL if has_archive_selection else tk.DISABLED)
        self.extract_selected_btn.config(state=tk.NORMAL if has_archive_selection else tk.DISABLED)
        self.extract_all_btn.config(state=tk.NORMAL if has_archive else tk.DISABLED)

    def _set_status(self, message: str):
        """Update status bar message."""
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def _add_files(self):
        """Add files to selection list."""
        files = filedialog.askopenfilenames(
            title="Select Text Files",
            initialdir=self.last_directory,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if files:
            for file_path in files:
                path = Path(file_path)
                if path not in self.selected_files:
                    self.selected_files.append(path)
                    self.file_listbox.insert(tk.END, path.name)

            self.last_directory = Path(files[0]).parent
            self._set_status(f"Added {len(files)} file(s)")
            self._update_button_states()

    def _add_directory(self):
        """Add directory to selection list (recursively scanned)."""
        directory = filedialog.askdirectory(
            title="Select Directory",
            initialdir=self.last_directory
        )

        if directory:
            dir_path = Path(directory)
            if dir_path not in self.selected_files:
                self.selected_files.append(dir_path)
                self.file_listbox.insert(tk.END, f"📁 {dir_path.name}/")

            self.last_directory = dir_path.parent
            self._set_status(f"Added directory: {dir_path.name}")
            self._update_button_states()

    def _remove_selected(self):
        """Remove selected files from list."""
        selection = self.file_listbox.curselection()
        if not selection:
            return

        # Remove in reverse order to maintain indices
        for index in reversed(selection):
            self.file_listbox.delete(index)
            del self.selected_files[index]

        self._set_status(f"Removed {len(selection)} file(s)")
        self._update_button_states()

    def _clear_all(self):
        """Clear all files from selection list."""
        self.selected_files.clear()
        self.file_listbox.delete(0, tk.END)
        self._set_status("Cleared all files")
        self._update_button_states()

    def _compress_to_archive(self):
        """Compress selected files to archive."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please add files to compress first.")
            return

        # Ask for output file
        output_file = filedialog.asksaveasfilename(
            title="Save Archive As",
            initialdir=self.last_directory,
            defaultextension="._t_",
            filetypes=[("TextCompressor Archive", "*._t_"), ("All files", "*.*")]
        )

        if not output_file:
            return

        output_path = Path(output_file)
        self.last_directory = output_path.parent

        try:
            self._set_status("Compressing files...")
            self.root.update()

            # Create archive
            stats = create_archive(self.selected_files, output_path)

            # Update status
            ratio_percent = stats['ratio'] * 100
            self.ratio_label.config(
                text=f"Compression ratio: {ratio_percent:.1f}% "
                     f"({stats['compressed_size']:,} / {stats['original_size']:,} bytes)"
            )

            self._set_status(
                f"Archive created: {output_path.name} - "
                f"{stats['file_count']} files, {ratio_percent:.1f}% compression"
            )

            messagebox.showinfo(
                "Success",
                f"Archive created successfully!\n\n"
                f"Files: {stats['file_count']}\n"
                f"Original size: {stats['original_size']:,} bytes\n"
                f"Compressed size: {stats['compressed_size']:,} bytes\n"
                f"Compression ratio: {ratio_percent:.1f}%"
            )

        except Exception as e:
            self._set_status("Error during compression")
            messagebox.showerror("Compression Error", f"Failed to create archive:\n{e}")

    def _extract_archive_dialog(self):
        """Open dialog to select and extract an archive."""
        archive_file = filedialog.askopenfilename(
            title="Select Archive to Extract",
            initialdir=self.last_directory,
            filetypes=[("TextCompressor Archive", "*._t_"), ("All files", "*.*")]
        )

        if not archive_file:
            return

        archive_path = Path(archive_file)
        self.last_directory = archive_path.parent

        # Ask for output directory
        output_dir = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.last_directory
        )

        if not output_dir:
            return

        output_path = Path(output_dir)

        try:
            self._set_status("Extracting archive...")
            self.root.update()

            extracted = extract_all(archive_path, output_path)

            self._set_status(f"Extracted {len(extracted)} files to {output_path}")
            messagebox.showinfo(
                "Success",
                f"Extracted {len(extracted)} file(s) to:\n{output_path}"
            )

        except Exception as e:
            self._set_status("Error during extraction")
            messagebox.showerror("Extraction Error", f"Failed to extract archive:\n{e}")

    def _browse_archive(self):
        """Browse and load archive for inspection."""
        archive_file = filedialog.askopenfilename(
            title="Browse Archive",
            initialdir=self.last_directory,
            filetypes=[("TextCompressor Archive", "*._t_"), ("All files", "*.*")]
        )

        if not archive_file:
            return

        archive_path = Path(archive_file)
        self.last_directory = archive_path.parent

        try:
            self._set_status("Loading archive...")
            self.root.update()

            # Load archive file list
            self.current_archive = archive_path
            self.archive_files = list_archive(archive_path)

            # Update listbox
            self.archive_listbox.delete(0, tk.END)
            for file_info in self.archive_files:
                display_text = f"{file_info['name']} ({file_info['token_count']} tokens)"
                self.archive_listbox.insert(tk.END, display_text)

            self._set_status(f"Loaded archive: {archive_path.name} ({len(self.archive_files)} files)")
            self._update_button_states()

        except Exception as e:
            self._set_status("Error loading archive")
            messagebox.showerror("Archive Error", f"Failed to load archive:\n{e}")

    def _preview_selected(self):
        """Preview selected file from archive."""
        selection = self.archive_listbox.curselection()
        if not selection or not self.current_archive:
            return

        index = selection[0]
        file_info = self.archive_files[index]
        filename = file_info['name']

        try:
            self._set_status(f"Loading preview of {filename}...")
            self.root.update()

            # Get file content
            content = preview_file(self.current_archive, filename)

            # Update preview text widget
            self.preview_text.config(state=tk.NORMAL)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, content)
            self.preview_text.config(state=tk.DISABLED)

            self._set_status(f"Previewing: {filename}")

        except Exception as e:
            self._set_status("Error loading preview")
            messagebox.showerror("Preview Error", f"Failed to preview file:\n{e}")

    def _extract_selected(self):
        """Extract selected file from archive."""
        selection = self.archive_listbox.curselection()
        if not selection or not self.current_archive:
            return

        index = selection[0]
        file_info = self.archive_files[index]
        filename = file_info['name']

        # Ask for output location
        output_file = filedialog.asksaveasfilename(
            title="Save Extracted File As",
            initialdir=self.last_directory,
            initialfile=filename,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if not output_file:
            return

        output_path = Path(output_file)
        self.last_directory = output_path.parent

        try:
            self._set_status(f"Extracting {filename}...")
            self.root.update()

            extract_from_archive(self.current_archive, filename, output_path)

            self._set_status(f"Extracted: {filename}")
            messagebox.showinfo("Success", f"File extracted to:\n{output_path}")

        except Exception as e:
            self._set_status("Error during extraction")
            messagebox.showerror("Extraction Error", f"Failed to extract file:\n{e}")

    def _extract_all(self):
        """Extract all files from current archive."""
        if not self.current_archive:
            return

        # Ask for output directory
        output_dir = filedialog.askdirectory(
            title="Select Output Directory for All Files",
            initialdir=self.last_directory
        )

        if not output_dir:
            return

        output_path = Path(output_dir)

        try:
            self._set_status("Extracting all files...")
            self.root.update()

            extracted = extract_all(self.current_archive, output_path)

            self._set_status(f"Extracted {len(extracted)} files")
            messagebox.showinfo(
                "Success",
                f"Extracted {len(extracted)} file(s) to:\n{output_path}"
            )

        except Exception as e:
            self._set_status("Error during extraction")
            messagebox.showerror("Extraction Error", f"Failed to extract files:\n{e}")


def main():
    """Run the GUI application."""
    root = tk.Tk()
    app = TextCompressorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
