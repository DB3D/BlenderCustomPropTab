# SPDX-FileCopyrightText: 2025 BD3D DIGITAL DESIGN (Dorian B.)
#
# SPDX-License-Identifier: GPL-2.0-or-later

#################################################################################################################################
# READ ME
#
# How to Use?
# 1 - Add this file to your add-on folder as a separate module. 
#     Don't edit the file please, just use the public functions.
#
# 2 - In your code, create some panels (from bpy.types.Panel)
#     - Follow the regular `_PT_` panel registration procedure.
#     - Define `.draw(self, context)` and `.bl_label` as usual.
#     - Regroup all these panels in a list, that you'll pass later to 'append_tab()'
#     - Nothing else is required to you. Do not use 'bpy.utils.register_class' nor 'unregister_class'.
#
# 3 - Implement the `customtab.register()` and `customtab.unregister()` functions in your main `__init__.py`:
#     - Attach these functions to your main add-on's `register()` and `unregister()` functions, respectively.
#     - Important: Ensure that you register your panels BEFORE registering this module!
#
# 4 - Add your custom tabs using the `customtab.append_tab()` function. For example:
#     ```
#     append_tab(uniqueid="SUPERTAB", icon="MONKEY", name="My Monkey Tab", description="Suzanne is King", panels=panelslistMonkey,)
#     append_tab(uniqueid="MYUNIQUENAME", icon="GHOST_ENABLED", name="Ghost Tab", panels=panellistGhost,)
#     ```
#     - Important: Use a unique `uniqueid` to avoid conflicts with other tools.
#
# Note:
# - Do not access the internal functions of this module (functions starting with `_`) 
#   or modify global variables in uppercase.
# - If you are performing procedural unregistration of classes based on their module path, 
#   avoid automatically registering classes created by this module.
# - Please avoid loading too many custom tabs, and make sure your tool actually deserved to be placed in such editor.
#   Keep in mind, we don't want this place to be overcrowded too quickly!
# 
# Important:
# - Please do not modify the code, or implement your own version of this trick.
#   This solution can ONLY work if we don't step on each others space, we need to use th same norm. 
#   Why? Because only one patch can be executed per blender session, 
#   and many plugins might integrate this module.

DEBUG_MODE = False

module_info = {
    'version':(1,0),
    'blender_version_min':(4,2,0),
}

#################################################################################################################################

# NOTE: About
# This code monkey-patches Blender's UI to extend functionality.
# Due to limitations in Blender's public Python API, creative solutions are required, as 
# what we are trying to achieve is impossible through conventional methods.
# If all plugins follow the same conventions, conflicts should be minimal.

# NOTE: How does it work?
# - Navigation of the Properties editor is done via 'space.context'. 
#   Constraint: Unfortunately, this enum is read-only, and we cannot add anything to it.
#   Solution: So what we'll do instead is impost the draw function of 'PROPERTIES_PT_navigation_bar' with our own Enum that mimics the original.
#
# - Constraint: There's no way to register a Python property per SpaceProperties for our new TabEnum, 
#   Solution: we are automatically registering as many tab EnumProperties for every PropertiesEditor from their memory address.
#
# - Essentially, when you navigate on the properties editor, you'll not use 'space.context' anymore, 
#   but a unique equivalent window_manager.EnumProperty per editor.
#
# - When you interact with this Enum, 'space.context' will be adjusted accordingly.
#
# - Because the Enums use the '_generate_enumitems' function to define their contents, we are able to dynamically define
#   our tabs' elements.
#
# - When you choose a custom tab that does not exist natively in Blender, 'space.context' will be set to 'TOOL', and
#   the space will be hijacked with the given panels.
#
# - Because this code can be executed multiple times, as it can be hosted by multiple tools in the same Blender session, 
#   we took extra care to register/unregister Properties, Classes, and panels only when needed.

# TODO: 
# - Fix the horrible try-except for tab context; might do two in one with the solution below.
# - Fix the problem when swapping the active object. The tab might change, but not the enum active index.
#   We could fix this with a context.object msgbus, perhaps. Or, we define precise poll behaviors of tabs; when polling changes, we act on the index.
# - Test if custom icon integer are working on panel as well.
# - Problem with spacers if tabs are disappearing; use spacer_after instead of spacer.
# - Bonus:
#   - What about panel search? What we need to do is highlight proper active items, just that.
#   - Toggle_pin button. Custom operator?
#   - FInd unregistration solution

import bpy
import os
from collections.abc import Iterable
import importlib.util

# oooooooooo.                 .             
# `888'   `Y8b              .o8             
#  888      888  .oooo.   .o888oo  .oooo.   
#  888      888 `P  )88b    888   `P  )88b  
#  888      888  .oP"888    888    .oP"888  
#  888     d88' d8(  888    888 . d8(  888  
# o888bood8P'   `Y888""8o   "888" `Y888""8o 

# the native possible items
EXISTING_ITEMS = [
    {'id':'TOOL',            'icon':'TOOL_SETTINGS',   'poll':None, 'name':"Tool",             'description':"Active Tool and Workspace settings",},
    None,
    {'id':'RENDER',          'icon':'SCENE',           'poll':None, 'name':"Render",           'description':"Render Properties",},
    {'id':'OUTPUT',          'icon':'OUTPUT',          'poll':None, 'name':"Output",           'description':"Output Properties",},
    {'id':'VIEW_LAYER',      'icon':'RENDERLAYERS',    'poll':None, 'name':"View Layer",       'description':"View Layer Properties",},
    {'id':'SCENE',           'icon':'SCENE_DATA',      'poll':None, 'name':"Scene",            'description':"Scene Properties",},
    {'id':'WORLD',           'icon':'WORLD',           'poll':None, 'name':"World",            'description':"World Properties",},
    None,
    {'id':'COLLECTION',      'icon':'GROUP',           'poll':None, 'name':"Collection",       'description':"Collection Properties",},
    None,
    {'id':'OBJECT',          'icon':'OBJECT_DATA',     'poll':None, 'name':"Object",           'description':"Object Properties",},
    {'id':'MODIFIER',        'icon':'MODIFIER',        'poll':None, 'name':"Modifiers",        'description':"Modifier Properties",},
    {'id':'SHADERFX',        'icon':'SHADERFX',        'poll':None, 'name':"Effects",          'description':"Visual Effects Properties",},
    {'id':'PARTICLES',       'icon':'PARTICLES',       'poll':None, 'name':"Particles",        'description':"Particle Properties",},
    {'id':'PHYSICS',         'icon':'PHYSICS',         'poll':None, 'name':"Physics",          'description':"Physics Properties",},
    {'id':'CONSTRAINT',      'icon':'CONSTRAINT',      'poll':None, 'name':"Constraints",      'description':"Object Constraint Properties",},
    {'id':'DATA',            'icon':'*DATA_SPECIAL*',  'poll':None, 'name':"Data",             'description':"Object Data Properties",},
    {'id':'BONE',            'icon':'BONE_DATA',       'poll':None, 'name':"Bone",             'description':"Bone Properties",},
    {'id':'BONE_CONSTRAINT', 'icon':'CONSTRAINT_BONE', 'poll':None, 'name':"Bone Constraints", 'description':"Bone Constraint Properties",},
    {'id':'MATERIAL',        'icon':'MATERIAL',        'poll':None, 'name':"Material",         'description':"Material Properties",},
    None,
    {'id':'TEXTURE',         'icon':'TEXTURE',         'poll':None, 'name':"Texture",          'description':"Texture Properties",},
    ]

POSSIBLE_NATIVE_ENTRIES = [
    e['id']
    for e in EXISTING_ITEMS 
    if type(e) is dict
    ]


# ooooo     ooo     .    o8o  oooo           
# `888'     `8'   .o8    `"'  `888           
#  888       8  .o888oo oooo   888   .oooo.o 
#  888       8    888   `888   888  d88(  "8 
#  888       8    888    888   888  `"Y88b.  
#  `88.    .8'    888 .  888   888  o.  )88b 
#    `YbodP'      "888" o888o o888o 8""888P' 

def _dprint(*args):
    """debug print"""
    if DEBUG_MODE:
        return print(*args)
    return None
    
def _all_properties_spaces(context=None):
    """return a generator of all properties areas space"""
    if (context is None):
        context = bpy.context
    wm = context.window_manager
    for w in wm.windows:
        for a in w.screen.areas:
            if (a.type == 'PROPERTIES'):
                for s in a.spaces:
                    if (s.type == 'PROPERTIES'):
                        yield s

def _all_handlers():
    """return a list of handler stored in .blend""" 
    for oh in bpy.app.handlers:
        if isinstance(oh, Iterable):
            for h in oh:
                yield h

def _get_dataicon_fromcontext(obj=None) -> str:
    """Return a DATA icon corresponding to the object data type. Will use context.obj if None"""

    if (obj is None):
        obj = bpy.context.active_object
    if (not obj):
        return 'QUESTION'

    icons = {
        'MESH': 'MESH_DATA',
        'CURVE': 'CURVE_DATA',
        'SURFACE': 'SURFACE_DATA',
        'META': 'META_DATA',
        'FONT': 'FONT_DATA',
        'VOLUME': 'VOLUME_DATA',
        'LIGHT': 'LIGHT_DATA',
        'GREASEPENCIL': 'OUTLINER_DATA_GREASEPENCIL',
        'CAMERA': 'CAMERA_DATA',
        'ARMATURE': 'ARMATURE_DATA',
        'LATTICE': 'LATTICE_DATA',
        'EMPTY': 'EMPTY_DATA',
        'LIGHT_PROBE': 'LIGHTPROBE_SPHERE',
        'SPEAKER': 'SPEAKER',
        }
    
    corresponding = icons.get(obj.type, 'QUESTION')

    if corresponding=='EMPTY_DATA':
        if type(obj.data) is bpy.types.Image:
            corresponding = 'IMAGE_DATA'

    return corresponding

# oooooooooooo                                            
# `888'     `8                                            
#  888         oooo  oooo  ooo. .oo.    .ooooo.   .oooo.o 
#  888oooo8    `888  `888  `888P"Y88b  d88' `"Y8 d88(  "8 
#  888    "     888   888   888   888  888       `"Y88b.  
#  888          888   888   888   888  888   .o8 o.  )88b 
# o888o         `V88V"V8P' o888o o888o `Y8bod8P' 8""888P' 


def get_customtab_propname(space) -> str:
    """get the customtab window_manager.TabCustEnumProperty propname depending on the given space.
    Each of your properties space will consequently generate a new window_manager.enum with an unique 
    propname depending on your space memory adress."""

    if (space.type != 'PROPERTIES'):
        print(f"WARNING: Given space is not of type 'PROPERTIES'\nFrom module instance: {__file__}")
        return None

    moduleidentifier = 'TabCustv1'
    memadress = space.as_pointer()
    return f'{moduleidentifier}_enum{memadress}'

def get_customtab_value(space):
    """Get the window_manager.TabCustEnumProperty value equivalent for a given space. 
    Each of your properties space will consequently generate a new window_manager.enum with an unique name.
    Will return None if not found"""

    if (space.type != 'PROPERTIES'):
        print(f"WARNING: Given space is not of type 'PROPERTIES'\nFrom module instance: {__file__}")
        return None

    wm = bpy.context.window_manager
    dynpropname = get_customtab_propname(space)
    return getattr(wm,dynpropname,None)

def sync_spacecontext(propname, context=None,):
    """Ensure Properties space.context Enum value is in sync with their window_manager.TabCustEnumProperty counterpart"""

    if (context is None):
        context = bpy.context

    wm = context.window_manager
    selected = getattr(wm, propname)

    # If the user chose a custom enum entry, then we set the active tab to tool.
    # all custom panels use the tool tab 
    if (selected not in POSSIBLE_NATIVE_ENTRIES):
        selected = 'TOOL'

    # we synchronize context value
    for s in _all_properties_spaces(context):
        spacepropid = get_customtab_propname(s)
        if (spacepropid == propname):
            s.context = selected

    return None

def sync_customtab(space,):
    """Ensure the window_manager.TabCustEnumProperty values are in sync with the counterpart Properties space.context"""

    if not hasattr(space,'context'):
        return None

    dynpropname = get_customtab_propname(space)
    wm = bpy.context.window_manager

    current_val = getattr(wm,dynpropname,None)
    if (current_val is None):
        print(f"WARNING: sync_customtab() didn't find prop '{dynpropname}'. Set kwarg 'create_prop_if_needed' to True, in order to create it if needed.\nFrom module instance: {__file__}")
        return None

    if (current_val != space.context):
        setattr(wm,dynpropname,space.context)

    return None


def _generate_enumitems(context, space) -> list:
    """generate an enum list depending on context space and encoded globals"""

    wm = bpy.context.window_manager
    if space is None:
        return None
    if (space.type!='PROPERTIES'):
        return None

    #We need to imitate the native behavior of space.context 
    # so we fill the Enumitems with the compatible native entries, depending on context!
    old_context = str(space.context)
    r, i = [], 0
    for v in EXISTING_ITEMS:

        #None are spacers
        if (v is None):
            # we don't draw two spacers in a row!
            if (r and r[-1] is None):
                continue
            r.append(None)
            continue

        # TODO IMPORTANT to fix later.. 
        # Lazy dirty solution to check if the items are available. We can't use this on the long term because this function is executing constantly.
        # Unsure how to easily get what's available depending on context. Perhaps need to define conditions manually. i hope not..
        try: space.context = v['id']
        except: continue

        uniqueid, icon, poll = v['id'], v['icon'], v['poll']

        #support for tab poll functions
        if (poll):
            try:
                if (not poll(context)):
                    continue
            except Exception as e:
                print(f"WARNING: tab uniqueid '{uniqueid}' poll function failed!\n{e}\nFrom module instance: {__file__}")
                continue

        #icons of mesh data varies depending on active object.
        if (icon=='*DATA_SPECIAL*'):
            icon = _get_dataicon_fromcontext()

        r.append((uniqueid, v['name'], v['description'], icon, i))
        i += 1
        continue

    #restore our try except bs trick above.
    space.context = old_context

    #Fill our enum items with the added custom elements then!
    for v in _get_registry():
        
        #None are spacers
        if (v is None):
            # we don't draw two spacers in a row!
            if (len(r)) and (r[-1]==None):
                continue
            r.append(None)
            continue

        uniqueid, icon, poll = v['id'], v['icon'], v['poll']

        #support for tab poll functions
        if (poll):
            try:
                if (not poll(context)):
                    continue
            except Exception as e:
                print(f"WARNING: tab uniqueid '{uniqueid}' poll function failed!\n{e}\nFrom module instance: {__file__}")
                continue

        r.append((uniqueid, v['name'], v['description'], icon, i))
        i += 1
        continue

    return r

def _reg_enumproperty_for_space(space):
    """Dynamically register a Enumproperty on WindowManager using space.as_pointer() as name"""

    dynpropname = get_customtab_propname(space)

    #no need to register if already exists!
    if hasattr(bpy.types.WindowManager, dynpropname):
        return None

    current_items = _generate_enumitems(bpy.context, space)
    default_idx = [t[4] for t in current_items if (type(t) is tuple) and (t[0]==space.context)][0]

    prop = bpy.props.EnumProperty(
        name="Properties Tab",
        default=default_idx,
        items=lambda self, context: _generate_enumitems(context, context.space_data),
        update=lambda self, context: sync_spacecontext(dynpropname, context=context,),
        )

    print(f"DynamicReg:{dynpropname}")
    setattr(bpy.types.WindowManager, dynpropname, prop)

    return None

#Registry is a global list containing None or Dicts of strings or function we store on bpy.types.WindowManager
#Similar struct to EXISTING_ITEMS, but with added header, poll functions

def _get_registry():
    wm = bpy.context.window_manager
    if not hasattr(wm,'TabCustomv1Registry'):
        bpy.types.WindowManager.TabCustomv1Registry = []
    return wm.TabCustomv1Registry

def _del_registry():
    wm = bpy.context.window_manager
    for wm in bpy.data.window_managers:
        if hasattr(wm,'TabCustomv1Registry'):
            wm.TabCustomv1Registry.clear()
    if hasattr(bpy.types.WindowManager,'TabCustomv1Registry'):
        del bpy.types.WindowManager.TabCustomv1Registry
    return None

def _append_registry(item):
    _get_registry().append(item)
    return None

def _remove_from_registry(uniqueid):
    torem = None
    registry = _get_registry()
    for d in registry:
        if (type(d) is dict):
            if d['id']==uniqueid:
                torem = d
                break
    if torem:
        registry.remove(torem)
    return None

def _existing_registry_ids():
    for d in _get_registry():
        if (type(d) is dict):
            yield d['id']

def _get_from_registry(uniqueid:str, attribute:str,):
    for d in _get_registry():
        if (type(d) is dict) and (d['id']==uniqueid):
            return d.get(attribute)
    return None

# ooooo   ooooo                             .o8  oooo                              
# `888'   `888'                            "888  `888                              
#  888     888   .oooo.   ooo. .oo.    .oooo888   888   .ooooo.  oooo d8b  .oooo.o 
#  888ooooo888  `P  )88b  `888P"Y88b  d88' `888   888  d88' `88b `888""8P d88(  "8 
#  888     888   .oP"888   888   888  888   888   888  888ooo888  888     `"Y88b.  
#  888     888  d8(  888   888   888  888   888   888  888    .o  888     o.  )88b 
# o888o   o888o `Y888""8o o888o o888o `Y8bod88P" o888o `Y8bod8P' d888b    8""888P' 

#Private functions, please don't use them.

def _timerfunc():
    """function executed reccurently. In here we register any new Ui property user might need!"""
    #Warning, context access from a timer is exessively frustrating

    context = bpy.context
    for s in _all_properties_spaces(context):
        _reg_enumproperty_for_space(s)

    return 0.4

def _reg_timers(regstatus:bool):
    """register our timers"""

    match regstatus:

        case True:
            
            #many instance of this code might be run across many addons. Only one timer need to be active
            wm = bpy.context.window_manager
            if hasattr(wm,'TabCustv1_timerflag'):
                return None

            bpy.types.WindowManager.TabCustv1_timerflag = bpy.props.BoolProperty(
                name="TabCust Timer Registered",
                description="No need to register more timers",
                default=True,
                )
            bpy.app.timers.register(_timerfunc, persistent=True)
        
        case False:
            bpy.app.timers.unregister(_timerfunc)

    return None

@bpy.app.handlers.persistent
def _handlerfct_TabCustv1_post(_): #needed an unique fct name
    """update on depsgraph change"""

    context = bpy.context
    for s in _all_properties_spaces(context):
        _reg_enumproperty_for_space(s)

    return None

@bpy.app.handlers.persistent
def _handlerfct_TabCustv1_load(_): #needed an unique fct name
    """Handler function when user is loading a file"""

    return _reg_timers(True)

def _reg_handlers(regstatus:bool):
    """register handlers by name to avoid doubles"""

    match regstatus:

        case True:
            handler_names = [h.__name__ for h in _all_handlers()]
            if ('_handlerfct_TabCustv1_post' not in handler_names):
                bpy.app.handlers.depsgraph_update_post.append(_handlerfct_TabCustv1_post)
            if ('_handlerfct_TabCustv1_load' not in handler_names):
                bpy.app.handlers.load_post.append(_handlerfct_TabCustv1_load)
        
        case False:
            for h in _all_handlers():
                if(h.__name__=='_handlerfct_TabCustv1_post'):
                    bpy.app.handlers.depsgraph_update_post.remove(h)
                if(h.__name__=='_handlerfct_TabCustv1_load'):
                    bpy.app.handlers.load_post.remove(h)

    return None 

# ooooo                                                     .   
# `888'                                                   .o8   
#  888  ooo. .oo.  .oo.   oo.ooooo.   .ooooo.   .oooo.o .o888oo 
#  888  `888P"Y88bP"Y88b   888' `88b d88' `88b d88(  "8   888   
#  888   888   888   888   888   888 888   888 `"Y88b.    888   
#  888   888   888   888   888   888 888   888 o.  )88b   888 . 
# o888o o888o o888o o888o  888bod8P' `Y8bod8P' 8""888P'   "888" 
#                          888                                  
#                         o888o                                 

ORIGINAL_CLASSES = []
PATCHED_CLASSES = []

def _reg_tool_impostors(regstatus:bool):
    """monkey patching the draw/poll functions of the tool Properties category.
    we chose this section as it is mostly deserted, and unaffected by context"""

    childrenreload = False
    classes_to_patch = []
    classes_children = []

    #gather the classes we need to patch. All type UI TOOL for View3D..
    for attr in dir(bpy.types):

        #we work with panels only
        if ('_PT_' not in attr):
            continue

        cls = getattr(bpy.types,attr)
        
        #user classes we skip. separate function for that.
        if hasattr(cls,'CustTabUniqueID'):
            continue

        #ensure the attributes are correct
        if not (hasattr(cls,'bl_region_type') and hasattr(cls,'bl_category') and hasattr(cls,'bl_space_type') \
                and (cls.bl_region_type=='UI' and cls.bl_category=="Tool" and cls.bl_space_type=='VIEW_3D')):
            continue
        
        #store children separately
        if hasattr(cls,'bl_parent_id'):
              classes_children.append(cls)
              continue

        classes_to_patch.append(cls)
        continue

    #proceed to the registration of patches
    match regstatus:

        case True:
            
            #NOTE for registration, we monkeypatch by reg/unreg the class entirely
            # because we use the same name as blender class, it will effectively replace it

            for ocl in classes_to_patch:

                #we register only non-registerepatchedd classes
                if hasattr(ocl, 'CustTabIsPatched'):
                    continue

                class Patched(ocl):
                    """exact copy of original Panel class, but with tweaked poll behavior"""
                    __name__ = ocl.__name__
                    bl_idname = ocl.__name__

                    CustTabIsPatched = True
                    CustTabIsHeader = ocl.__name__=='VIEW3D_PT_active_tool_duplicate'
                    if CustTabIsHeader:
                        bl_order = 0

                    original_draw = ocl.draw
                    original_poll = ocl.poll if hasattr(ocl,'poll') else None

                    def draw(self, context, *args, **kwargs):

                        layout = self.layout
                        space = context.space_data

                        #header of the editor. If tab is custom tool, we draw a custom header
                        if self.CustTabIsHeader:
                            if (space.type=='PROPERTIES' and space.context=='TOOL'):
                                tabval = get_customtab_value(space)
                                if (tabval!='TOOL'):

                                    #find back icon and name
                                    tabname = _get_from_registry(tabval,'name')
                                    tabicon = _get_from_registry(tabval,'icon')
                                    tabheader = _get_from_registry(tabval,'header')

                                    #draw a custom header function?
                                    if (tabheader):
                                        return tabheader(layout, context)

                                    #else we draw a little simple drawing
                                    row = layout.row()
                                    row_left = row.row()
                                    row_left.alignment = 'LEFT'
                                    row_right = row.row()
                                    row_right.alignment = 'RIGHT'

                                    if (tabicon):
                                        match tabicon:
                                            case str(): row_left.label(text='', icon=tabicon,)
                                            case int(): row_left.label(text='', icon_value=tabicon,)

                                    if (tabname):
                                        row_left.label(text=tabname)

                                    # TODO custom behavior for pin perhaps? Native pin was not designed for Tool context..
                                    # pin_icon = 'PINNED' if bool(space.pin_id) else 'UNPINNED'
                                    # row_right.operator("buttons.toggle_pin", text="", icon=pin_icon, emboss=False,)

                                    layout.separator(factor=0.5)
                                    return None

                        #debug data?
                        if (DEBUG_MODE):
                            layout.box().label(text="I'm Patched!", icon="GHOST_ENABLED")
                        return self.original_draw(context, *args, **kwargs)

                    @classmethod
                    def poll(cls, context, *args, **kwargs):
                        """matched poll function, custom behavior in properties now, need to look at window_manager.CustomTab value"""

                        space = context.space_data

                        #execute native poll function
                        original_cond = True
                        if cls.original_poll:
                            original_cond = cls.original_poll(context, *args, **kwargs)

                        #specific poll condictions if in TOOL context
                        added_cond = True
                        if (space.type=='PROPERTIES' and space.context=='TOOL'):
                            tabval = get_customtab_value(space)

                            #for headers panel, we always draw
                            if (cls.CustTabIsHeader):
                                  added_cond = True
                            else: added_cond = tabval in {'TOOL',None}

                        return original_cond and added_cond

                #store classes in global for unreg later.
                ORIGINAL_CLASSES.append(ocl)
                PATCHED_CLASSES.append(Patched)

                #proceed to unregister the original, and register the patched one
                _dprint('unload original and loading patch:',ocl)
                bpy.utils.unregister_class(ocl)
                bpy.utils.register_class(Patched)
                childrenreload = True

                continue

        case False:

            for pcl in PATCHED_CLASSES:

                #we unregister patch only!
                if not hasattr(pcl, 'CustTabIsPatched'):
                    continue

                #unregister our patches
                _dprint('unloading patch:',pcl)
                bpy.utils.unregister_class(pcl)

                #and register the original class instead
                for ocl in ORIGINAL_CLASSES:
                    if (ocl.__name__ == pcl.bl_idname):
                        _dprint('loading original:',pcl)
                        bpy.utils.register_class(ocl)

                childrenreload = True
                continue

            PATCHED_CLASSES.clear()
            ORIGINAL_CLASSES.clear()

    #when we reg/unreg a panel, we need to refresh children.
    if childrenreload:
        for ocl in classes_children:
            _dprint('reloading children:',ocl)
            bpy.utils.unregister_class(ocl)
            bpy.utils.register_class(ocl)

    return None

USER_PANELS = []

def _reg_userpanel(panel, uniqueid):
    """Register bpy.types.Panel of a tab via this operator"""

    global USER_PANELS

    #we work with panels only
    if not issubclass(panel, bpy.types.Panel):
        raise Exception(f"CustomTab: Please pass a Panel type, subclass of bpy.types.Panel\nFor panel {panel}")
    if ('_PT_' not in panel.__name__):
        raise Exception(f"CustomTab: Any blender panels should contain the keyword '_PT_'. Please read blender doc!\nFor panel {panel}")

    #we register only non-registerepatchedd classes
    if hasattr(panel, 'CustTabIsPatched'):
        raise Exception(f"CustomTab: It seems that you already have registered the Panel '{panel}'.")

    class PatchPanel(panel):
        """exact copy of original Panel class, but with tweaked poll behavior"""
        __name__ = panel.__name__

        bl_region_type = 'UI'
        bl_category = 'Tool'
        bl_space_type = 'VIEW_3D'
        bl_idname = panel.__name__
        
        CustTabUniqueID = uniqueid
        CustTabIsPatched = True
        CustTabIsHeader = False

        original_poll = panel.poll if hasattr(panel,'poll') else None

        @classmethod
        def poll(cls, context, *args, **kwargs):
            """matched poll function, custom behavior in properties now, need to look at window_manager.CustomTab value"""

            space = context.space_data
            if (space.type!='PROPERTIES'):
                return False
            if (space.context!='TOOL'):
                return False

            #execute native poll function
            original_cond = True
            if cls.original_poll:
                original_cond = cls.original_poll(context, *args, **kwargs)

            #specific poll condictions if in TOOL context
            return original_cond and get_customtab_value(space) == cls.CustTabUniqueID

    bpy.utils.register_class(PatchPanel)
    USER_PANELS.append(PatchPanel)

    return None

#Global, we'll store original blender draw function here
NATIVE_NAVDRAW = None

def _reg_nav_impostors(regstatus:bool):
    """Monkey patching a blender draw function"""

    global NATIVE_NAVDRAW
    cls = bpy.types.PROPERTIES_PT_navigation_bar

    match regstatus:

        case True:

            # many instance of this code might be run across many addons. 
            # Only one draw impostor needed!
            if hasattr(cls.draw,"TabCustImpostor"):
                return None

            def impostdraw(self, context):
                """will monkey patch PROPERTIES_PT_navigation_bar.draw"""

                wm = context.window_manager
                space = context.space_data

                layout = self.layout
                layout.scale_x = 1.4
                layout.scale_y = 1.4

                data, propname = wm, get_customtab_propname(space)

                #fallback if property not created yet
                if not hasattr(wm,propname):
                    #print("WARNING: CustomTabEnum for a space has not been created yet.\nFrom module instance: {__file__}")
                    data, propname = space, "context"

                if (space.search_filter):
                      layout.prop_tabs_enum(data, propname, icon_only=True, data_highlight=space, property_highlight="tab_search_results",)
                else: layout.prop_tabs_enum(data, propname, icon_only=True)

                return None

            impostdraw.TabCustImpostor = True
    
            NATIVE_NAVDRAW = cls.draw
            cls.draw = impostdraw

        case False:
            if (NATIVE_NAVDRAW is not None):
                cls.draw = NATIVE_NAVDRAW
                NATIVE_NAVDRAW = None

    return None

# ooooooooo.                        
# `888   `Y88.                      
#  888   .d88'  .ooooo.   .oooooooo 
#  888ooo88P'  d88' `88b 888' `88b  
#  888`88b.    888ooo888 888   888  
#  888  `88b.  888    .o `88bod8P'  
# o888o  o888o `Y8bod8P' `8oooooo.  
#                        d"     YD  
#                        "Y88888P'  

IDAPPENDED_TO_REGISTRY = []

def append_tab(uniqueid:str="", icon:str|int="", name:str="", description:str="", poll=None, header=None, spacer=False, panels:list=None,):
    """Register a new tab into the system.

    You can either:
        - Pass a `uniqueid` (string), an `icon` (string or integer), and list of Panels to `panels`.
          with optional arguments:
            `name` (string) for the tab's display name
            `description` (string) for hover information, 
            `poll` (function) that takes `context` as an argument and returns a Boolean,
            `header` (function) that takes `layout` and `context` as arguments, for drawing a custom header.
        - Or set `spacer=True` to add a spacer between tabs.
    """

    global IDAPPENDED_TO_REGISTRY
    wm = bpy.context.window_manager
    
    if spacer:
        _append_registry(None)
        return None

    if not (uniqueid and icon and panels):
        raise Exception("Please make sure to pass a uniqueid string, an icon value, and a list of panels.")
    
    if (uniqueid in POSSIBLE_NATIVE_ENTRIES):
        raise Exception(f"The uniqueid '{uniqueid}' is taken by blender already.")
    
    if (uniqueid in _existing_registry_ids()):
        print(f"WARNING: The uniqueid '{uniqueid}' is taken by another user. Impossible to register the custom tab.\nFrom module instance: {__file__}")
        return None

    _append_registry({
        'id':uniqueid,
        'name':name,
        'description':description,
        'icon':icon,
        'poll':poll,
        'header':header,
        },)

    IDAPPENDED_TO_REGISTRY.append(uniqueid)
    
    for panel in panels:
        _reg_userpanel(panel, uniqueid)
    
    return None


def register():
    """the main customtab module register, execute on plugin load, after registering your panels."""

    wm = bpy.context.window_manager

    if hasattr(wm,"TabCustv1_usercount"):
        wm.TabCustv1_usercount += 1

    else:
        bpy.types.WindowManager.TabCustv1_usercount = bpy.props.IntProperty(name="How many users are using TabCustv1?", default=1,)
        _reg_timers(True)
        _reg_handlers(True)
        _reg_nav_impostors(True)
        _reg_tool_impostors(True)

    return None

def unregister():
    """the main customtab module unregister, execute me on plugin deload, before unregistering your panels."""

    global IDAPPENDED_TO_REGISTRY, USER_PANELS
    wm = bpy.context.window_manager

    # 'TabCustv1_usercount' should always be there if there are other plugins as
    # we unregister only on very last user unristration
    if not hasattr(wm,"TabCustv1_usercount"):
        print(f"WARNING: Wrong unregisteration.\nFrom module instance: {__file__}")

    wm.TabCustv1_usercount -= 1

    #remove our enum items from the public centralized registry
    for d in IDAPPENDED_TO_REGISTRY:
        _remove_from_registry(d)
    IDAPPENDED_TO_REGISTRY.clear()

    #unregister our user panels
    for panel in USER_PANELS:
        bpy.utils.unregister_class(panel)
    USER_PANELS.clear()
        
    # NOTE We do NOT Unregister. 
    # The functions will automatically clear themselves for the next blender session!

    # #We unregister all this only if no plugins are using it!
    # if (wm.TabCustv1_usercount <= 0):
    #     _reg_nav_impostors(False)
    #     _reg_tool_impostors(False)
    #     _reg_handlers(False)
    #     _reg_timers(False)
    #     _del_registry()

    #     # cleanup any dynamically registered props?
    #     delnames = set()
    #     for attr in dir(bpy.types.WindowManager):
    #         if attr.startswith('TabCustv1'):
    #             delnames.add(attr)
    #             try:
    #                 delattr(bpy.types.WindowManager, attr)
    #             except Exception as e:
    #                 print("An Exception occured, couldn't delete a Property.")
    #                 print(e)

    #     #some properties convert themselves to user props
    #     for name in delnames:
    #         for wm in bpy.data.window_managers:
    #             if name in wm:
    #                 del wm[name]

    return None
