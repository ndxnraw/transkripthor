"""Paged, keyboard-accessible transcript blocks with one inline text editor."""
import tkinter as tk
from tkinter import ttk
from ndtranskripthor.core.i18n import tr
from ndtranskripthor.exports.subtitles import timestamp


class TranscriptBlocks(ttk.Frame):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.editor = editor
        self.chosen = ()
        self.blocks = {}
        self.headings = {}
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(fill='both', expand=True)
        self.body = ttk.Frame(self.canvas)
        self.body_id = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self.resize)

    def resize(self, event):
        self.canvas.itemconfigure(self.body_id, width=event.width)
        for _, _, label in self.blocks.values():
            label.configure(wraplength=max(100, event.width-48))

    def wheel(self, event):
        self.canvas.yview_scroll(-int(event.delta/120), 'units')
        return 'break'

    def selection(self):
        return self.chosen

    def selection_set(self, key):
        self.chosen = (str(key),)

    def choose(self, key):
        self.selection_set(key)
        self.editor.select()
        return 'break'

    def render(self, indices):
        self.chosen = ()
        for child in self.body.winfo_children():
            child.destroy()
        self.blocks.clear()
        self.headings.clear()
        for index in indices:
            item = self.editor.segments[index]
            card = ttk.Frame(self.body, style='Panel.TFrame', padding=10)
            card.pack(fill='x', pady=(0, 8), padx=2)
            heading = ttk.Label(card, text=self.metadata(item), style='CardMuted.TLabel')
            self.headings[str(index)] = heading
            heading.pack(anchor='w')
            content = ttk.Frame(card, style='Card.TFrame')
            content.pack(fill='x', pady=(6, 0))
            label = ttk.Label(content, text=item['text'], style='Transcript.TLabel', wraplength=max(100, self.canvas.winfo_width()-48), takefocus=True)
            label.pack(fill='x')
            self.blocks[str(index)] = (card, content, label)
            for widget in (card, heading, label):
                widget.bind('<Button-1>', lambda _, key=index: self.choose(key))
                widget.bind('<Return>', lambda _, key=index: self.choose(key))
                widget.bind('<MouseWheel>', self.wheel)
            label.bind('<FocusIn>', lambda _, key=index: self.focus_block(key))
            label.bind('<FocusOut>', lambda _, w=label: w.configure(style='Transcript.TLabel'))
            self.editor.bind_keys(card)
        self.canvas.yview_moveto(0)

    def focus_block(self, index):
        self.blocks[str(index)][2].configure(style='Focus.Transcript.TLabel')
        self.reveal(index)

    @staticmethod
    def metadata(item):
        text = f'{timestamp(item["start"])} – {timestamp(item["end"])}  •  {item.get("language") or tr("language.auto")}'
        return text + ('  •  ' + item['speaker'] if item.get('speaker') else '')

    def refresh_speakers(self):
        # Keep the active Text, its undo stack, selection, cursor and scroll.
        for key, heading in self.headings.items():
            heading.configure(text=self.metadata(self.editor.segments[int(key)]))

    def edit(self, index, text):
        # Capture is called before this method; replace only the active field.
        for key, (card, content, label) in self.blocks.items():
            card.configure(style='Selected.TFrame' if key == str(index) else 'Panel.TFrame')
            for child in content.winfo_children():
                if child != label:
                    child.destroy()
            label.configure(text=self.editor.segments[int(key)]['text'])
            label.pack(fill='x')
        _, content, label = self.blocks[str(index)]
        label.pack_forget()
        field = tk.Text(content, wrap='word', height=4, undo=False, font=(self.editor.app.font, 11), relief='flat', padx=8, pady=8, highlightthickness=2, takefocus=True)
        field.insert('1.0', text)
        field.edit_modified(False)
        field.pack(fill='x')
        field.bind('<<Modified>>', self.editor.modified)
        from ndtranskripthor.presentation.accessibility import text_navigation
        text_navigation(field)
        self.editor.bind_keys(field)
        field.focus_set()
        self.editor.text = field
        self.editor.apply_theme()
        return field

    def reveal(self, index):
        self.update_idletasks()
        card = self.blocks[str(index)][0]
        height = max(1, self.body.winfo_height())
        self.canvas.yview_moveto(card.winfo_y()/height)
