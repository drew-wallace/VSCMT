Visual Studio Code Merge Tool
===========================

A Sublime Text plugin to help you solve merge conflicts based on how VSC does it.

Commands
---------

VSCMT helps with these commands: `Find Next Conflict` and `Show Conflict Files`.

Configuration
-------------

To configure the plugin you can use a user-settings file in your user folder. You can easily access this file over `Preferences` -> `VSCMT` -> `Settings - User`.

For information on which settings are available take a look at the commented default-settings file:

```js
{
    // The git path
    // by default the plugin assumes that git is in your path
    "git_path": "git",

    // Enable or disable the live matching of conflict areas
    // By default the plugin matches live
    "live_matching": true,

    // The color of the highlighting is called "scope" in Sublime Text,
    // to change this color you can choose a different scope.
    // This customization isn't easy, since you have to define your own
    // scope in your theme file.
    "matching_scope": "invalid",

    // This option enables the filling the conflict area with a color
    // By default the area will just be outlined
    "fill_conflict_area": false,

    // This option enables the outline of the conflict area
    // By default the area will just be outlined
    "outline_conflict_area": true,

    // This option changes the display of the "Show Conflict Files" functionality"
    // true: Show only the filesnames ("src/main.js" becomes "main.js")
    // false: Show relative path (from the root of the repository)
    // By default Git Conflict Resolver only shows the filename
    "show_only_filename": true
}
```

Shortcuts
---------

There are no default shortcuts, to add them open your user keybindings file and add a keybinding like the following:

    { "keys": ["ctrl+alt+f"], "command": "find_next_conflict" },
    { "keys": ["ctrl+alt+c"], "command": "list_conflict_files" }
