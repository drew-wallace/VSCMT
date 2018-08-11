import sublime
import sublime_plugin
import os

from .modules import conflict_re
from .modules import git_mixin
from .modules import messages as msgs
from .modules import settings

def find_conflict(view, begin=0):
    conflict_region = view.find(conflict_re.NO_NAMING_GROUPS_PATTERN, begin)

    if not conflict_region:
        conflict_region = view.find(conflict_re.NO_NAMING_GROUPS_PATTERN, 0)
        if not conflict_region:
            sublime.status_message(msgs.get('no_conflict_found'))
            return None

    return conflict_region

class FindNextConflict(sublime_plugin.TextCommand):
    def run(self, edit):
        # Reload settings
        settings.load()

        current_selection = self.view.sel()

        # Use the end of the current selection for the search, or use 0 if nothing is selected
        begin = 0
        if len(current_selection) > 0:
            begin = self.view.sel()[-1].end()

        conflict_region = find_conflict(self.view, begin)
        if conflict_region is None:
            return

        # Add the region to the selection
        self.view.show_at_center(conflict_region)
        current_selection.clear()
        current_selection.add(sublime.Region(conflict_region.a))


class ListConflictFiles(sublime_plugin.WindowCommand, git_mixin.GitMixin):
    def run(self):
        # Reload settings
        settings.load()

        # Ensure git executable is available
        if not self.git_executable_available():
            sublime.error_message(msgs.get('git_executable_not_found'))
            return

        self.git_repo = self.determine_git_repo()
        if not self.git_repo:
            sublime.status_message(msgs.get('no_git_repo_found'))
            return

        conflict_files = self.get_conflict_files()
        if not conflict_files:
            sublime.status_message(msgs.get('no_conflict_files_found', self.git_repo))
            return

        self.show_quickpanel_selection(conflict_files)

    def get_conflict_files(self):
        # Search for conflicts using git executable
        conflict_files = self.git_command(
            ["diff", "--name-only", "--diff-filter=U"],
            repo=self.git_repo
        )

        conflict_files = conflict_files.split('\n')
        # Remove empty strings and sort the list
        # (TODO: sort also filenames only?)
        return sorted([x for x in conflict_files if x])

    def get_representation_list(self, conflict_files):
        """Returns a list with only filenames if the 'show_only_filenames'
        option is set, otherwise it returns just a clone of the given list"""
        result = None
        if settings.get('show_only_filenames'):
            result = []
            for string in conflict_files:
                result.append(string.rpartition('/')[2])
        else:
            result = list(conflict_files)

        # Add an "Open all ..." option
        result.insert(0, msgs.get('open_all'))

        return result

    def show_quickpanel_selection(self, conflict_files):
        full_path = [os.path.join(self.git_repo, x) for x in conflict_files]
        show_files = self.get_representation_list(conflict_files)

        # Show the conflict files in the quickpanel and open them on selection
        def open_conflict(index):
            if index < 0:
                return
            elif index == 0:
                # Open all ...
                self.open_files(*full_path)
            else:
                self.open_files(full_path[index - 1])

        self.window.show_quick_panel(show_files, open_conflict)

    def open_files(self, *files):
        for file in files:
            # Workaround sublime issue #39 using sublime.set_timeout
            # (open_file() does not set cursor when run from a quick panel callback)
            sublime.set_timeout(
                lambda file=file: init_view(self.window.open_file(file)),
                0
            )

class ScanForConflicts(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        if settings.get('live_matching'):
            view.run_command('vscmt_highlight_conflicts')

    def on_load_async(self, view):
        if settings.get('live_matching'):
            view.run_command('vscmt_highlight_conflicts')

    def on_pre_save_async(self, view):
        if settings.get('live_matching'):
            view.run_command('vscmt_highlight_conflicts')

    def on_modified_async(self, view):
        if settings.get('live_matching'):
            view.run_command('vscmt_highlight_conflicts')

startHeaderMarker = '<<<<<<<';
commonAncestorsMarker = '|||||||';
splitterMarker = '=======';
endFooterMarker = '>>>>>>>';

STORAGE_KEY = 'VSCMT.{}.region_keys'

def set_region_keys(view, keys):
    setting_key = STORAGE_KEY.format(view.id())
    view.settings().set(setting_key, list(keys))

def add_region_key(view, key):
    setting_key = STORAGE_KEY.format(view.id())
    allKeys = get_regions_keys(view)
    allKeys.add(key)
    view.settings().set(setting_key, list(allKeys))

def get_regions_keys(view):
    setting_key = STORAGE_KEY.format(view.id())
    return set(view.settings().get(setting_key) or [])

class VscmtHighlightConflictsCommand(sublime_plugin.TextCommand):
    def excludeCurrentBounds(self, x):
        x.a = self.view.full_line(x.a).b
        x.b = x.b - 7
        return x

    def excludeIncomingBounds(self, x):
        x.a = self.view.full_line(x.a).b
        x.b = x.b - 7
        return x

    def includeConflictBounds(self, x):
        x.a = self.view.full_line(x.a).a
        x.b = self.view.full_line(x.b).b
        return x

    def clearAllRegions(self):
        view = self.view

        for region in get_regions_keys(view):
            view.erase_regions(region)
        set_region_keys(view, [])

    def handleButtonClick(self, href):
        view = self.view

        choice = href.split("-")[0]
        conflictIndex = href.split("-")[1]

        current = view.get_regions("vscmt-current-" + conflictIndex)[0]
        currentBody = view.get_regions("vscmt-current-body-" + conflictIndex)[0]
        conflictBorder = view.get_regions("vscmt-conflict-border-" + conflictIndex)[0]
        incomingBody = view.get_regions("vscmt-incoming-body-" + conflictIndex)[0]
        incoming = view.get_regions("vscmt-incoming-" + conflictIndex)[0]

        self.clearAllRegions()

        if choice == "current":
            view.run_command('remove_text', {'a': incoming.a, 'b': incoming.b})
            view.run_command('remove_text', {'a': incomingBody.a, 'b': incomingBody.b})
            view.run_command('remove_text', {'a': conflictBorder.a, 'b': conflictBorder.b})
            view.run_command('remove_text', {'a': current.a, 'b': current.b})
        elif choice == "incoming":
            view.run_command('remove_text', {'a': incoming.a, 'b': incoming.b})
            view.run_command('remove_text', {'a': conflictBorder.a, 'b': conflictBorder.b})
            view.run_command('remove_text', {'a': currentBody.a, 'b': currentBody.b})
            view.run_command('remove_text', {'a': current.a, 'b': current.b})
        elif choice == "both":
            view.run_command('remove_text', {'a': incoming.a, 'b': incoming.b})
            view.run_command('remove_text', {'a': conflictBorder.a, 'b': conflictBorder.b})
            view.run_command('remove_text', {'a': current.a, 'b': current.b})
        elif choice == "highlighted":
            selections = view.sel()
            removedRegions = []
            removeStart = current.a

            for index, selection in enumerate(selections):
                if incomingBody.contains(selection) and currentBody.contains(removeStart):
                    region = sublime.Region(removeStart, incomingBody.a)
                    removedRegions.append(region)
                    removeStart = incomingBody.a

                if currentBody.contains(selection):
                    region = sublime.Region(removeStart, min(selection.a, selection.b))
                    removedRegions.append(region)
                    removeStart = max(selection.a, selection.b)
                elif incomingBody.contains(selection) and incomingBody.contains(removeStart):
                    region = sublime.Region(removeStart, min(selection.a, selection.b))
                    removedRegions.append(region)
                    removeStart = max(selection.a, selection.b)

            lastRegion = sublime.Region(removeStart, incoming.b)
            removedRegions.append(lastRegion)

            removedRegions.reverse()
            for region in removedRegions:
                view.run_command('remove_text', {'a': region.a, 'b': region.b})

        self.buildRegions()
        self.buildPhantoms()

    def mapPhantoms(self, indexCurrent):
        view = self.view

        index = indexCurrent[0]
        current = indexCurrent[1]
        currentColor = '#9aa83a' # view.style_for_scope("string")['foreground']
        incomingColor = '#6089b4' # view.style_for_scope("variable.parameter")['foreground']
        bothColor = '#9a9b99' # view.style_for_scope("comment")['foreground']
        selectedColor = '#c4480a' # view.style()["highlight"]
        return sublime.Phantom(sublime.Region(view.line(current.a).b), '&nbsp;<a style="color: ' + currentColor + '" href="current-' + str(index) + '">Accept Current Change</a> | <a style="color: ' + incomingColor + '" href="incoming-' + str(index) + '">Accept Incoming Change</a> | <a style="color: ' + bothColor + '" href="both-' + str(index) + '">Accept Both Changes</a> | <a style="color: ' + selectedColor + '" href="highlighted-' + str(index) + '">Accept Highlighted Changes</a>', sublime.LAYOUT_INLINE, self.handleButtonClick)

    def buildRegions(self):
        view = self.view

        self.currents.clear()
        self.clearAllRegions()

        conflictsCount = 0
        currentConflict = None

        currents = view.find("<<<<<<<", 0)
        incomings = view.find_all(">>>>>>>")
        start = 0
        end = 0
        if len(view.find("<<<<<<<", 0)) > 0 and len(view.find_all(">>>>>>>")) > 0:
            start = currents.a
            end = incomings[-1].b

        for line in view.lines(sublime.Region(start, end)):
            # Ignore empty lines
            if view.substr(line) == "" or view.substr(line).isspace():
                continue

            # Is this a start line? <<<<<<<
            if view.substr(line).startswith(startHeaderMarker):
                # Create a new conflict starting at this line
                currentConflict = {'startHeader': line, 'commonAncestors': [], 'splitter': None, 'endFooter': None}

            # Are we within a conflict block and is this a common ancestors marker? |||||||
            elif currentConflict is not None and currentConflict.get('splitter') is None and view.substr(line).startswith(commonAncestorsMarker):
                currentConflict['commonAncestors'].append(line);

            # Are we within a conflict block and is this a splitter? =======
            elif currentConflict is not None and currentConflict.get('splitter') is None and view.substr(line).startswith(splitterMarker):
                currentConflict['splitter'] = line;

            # Are we within a conflict block and is this a footer? >>>>>>>
            elif currentConflict is not None and currentConflict.get('splitter') is not None and view.substr(line).startswith(endFooterMarker):
                currentConflict['endFooter'] = line;

                # Create a full descriptor from the lines that we matched.
                vscmtCurrentKey = "vscmt-current-" + str(conflictsCount)
                view.add_regions(vscmtCurrentKey, [view.full_line(currentConflict['startHeader'])])
                add_region_key(view, vscmtCurrentKey)
                self.currents.append(view.full_line(currentConflict['startHeader']))

                vscmtCurrentColorizedKey = "vscmt-current-colorized-" + str(conflictsCount)
                view.add_regions(vscmtCurrentColorizedKey, [currentConflict['startHeader']], "string")
                add_region_key(view, vscmtCurrentColorizedKey)

                vscmtCurrentBodyKey = "vscmt-current-body-" + str(conflictsCount)
                view.add_regions(vscmtCurrentBodyKey, [sublime.Region(view.full_line(currentConflict['startHeader']).b, currentConflict['splitter'].a)], "string", flags=sublime.DRAW_NO_FILL)
                add_region_key(view, vscmtCurrentBodyKey)

                vscmtConflictBorderKey = "vscmt-conflict-border-" + str(conflictsCount)
                view.add_regions(vscmtConflictBorderKey, [self.includeConflictBounds(currentConflict['splitter'])])
                add_region_key(view, vscmtConflictBorderKey)

                vscmtIncomingBodyKey = "vscmt-incoming-body-" + str(conflictsCount)
                view.add_regions(vscmtIncomingBodyKey, [sublime.Region(currentConflict['splitter'].b, currentConflict['endFooter'].a)], "variable.parameter", flags=sublime.DRAW_NO_FILL)
                add_region_key(view, vscmtIncomingBodyKey)

                vscmtIncomingKey = "vscmt-incoming-" + str(conflictsCount)
                view.add_regions(vscmtIncomingKey, [self.includeConflictBounds(currentConflict['endFooter'])], "variable.parameter")
                add_region_key(view, vscmtIncomingKey)

                # Reset the current conflict to be empty, so we can match the next
                # starting header marker.
                conflictsCount += 1
                currentConflict = None;

    def buildPhantoms(self):
        self.phantomSet.update([])
        phantoms = list(map(self.mapPhantoms, enumerate(self.currents)))
        self.phantomSet.update(phantoms)

    def run(self, edit):
        view = self.view

        self.currents = []
        self.edit = edit
        self.phantomSet = sublime.PhantomSet(view, "phantomSet")

        self.buildRegions()
        self.buildPhantoms()

class RemoveTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, a, b):
        region = sublime.Region(a, b)
        self.view.erase(edit, region)

def init_view(view):
    return  # TODO: Find a workaround for the cursor position bug

    if view.is_loading():
        sublime.set_timeout(lambda: init_view(view), 50)
    else:
        view.run_command("find_next_conflict")
