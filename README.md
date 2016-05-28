# LatexOutliner for SublimeText

Work in progress!

[Scrivener][scr]-style latex editing for SublimeText.

The technical realization is inspired by the [FileBrowser][fb] plugin.

[scr]: https://www.literatureandlatte.com/scrivener.php
[fb]: https://github.com/aziz/SublimeFileBrowser

## Set up
- Clone this repository to your packages directory
- Save a new project in SublimeText
- Command palette: "LatexOutliner: Set up project"
- press `?` for help in the outline view
- If the outline view is not responding e.g. after you close and open the project, close it and use "LatexOuteliner: Show outline on the left"

### Beamer
If you set the "beamer" property to true in the project settings, then each text snippet will be surrounded by a frame, and the frame title will be the title of the text snippet.

## Todos
- move cursor with j,k (for non-vintageous users)
- Enable build tex from outline view 

### Later
- export outline to filesystem
- import outline from filesystem
- move cursor to open text snippet in focus
- nicer style for outline view (check dired.hiddentmTheme)
- hide cursor?

### Wishlist
- Drag'n'Drop outline
- Context menus for mouse interaction
