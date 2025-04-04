# SPDX-FileCopyrightText: 2025 BD3D DIGITAL DESIGN (Dorian B.)
#
# SPDX-License-Identifier: GPL-2.0-or-later

# NOTE this file is an implementation example 
# see how the customtab module is used. 
# implement your own panels and plugin structure.

# NOTE general advice:
# - always use 'context.active_object' instead of 'context.object' in the Properties editor.

import bpy
import os
import bpy.utils.previews
from . import customtab #we import our customtab module. 

# Example with plugin icons.
ICONS = None

# Example of your plugin panels

class TEST_PT_1(bpy.types.Panel):
    bl_label = "My custom curve"
    @classmethod
    def poll(cls, context):
        return (context.active_object and context.active_object.type == 'CURVE')
    def draw(self, context):
        self.layout.label(text="CurveSpecial")

class TEST_PT_2(bpy.types.Panel):
    bl_label = "My custom panel"
    def draw(self, context):
        self.layout.label(text="Monkey")

class TEST_PT_3(bpy.types.Panel):
    bl_label = "My Monkey"
    @classmethod
    def poll(cls, context):
        return True
    def draw(self, context):
        self.layout.label(text="Monkey Label")

class TEST_PT_3child(bpy.types.Panel):
    bl_label = ""
    bl_parent_id = 'TEST_PT_3'
    def draw_header(self, context):
        self.layout.label(text="CustHeader", icon="MONKEY")
    @classmethod
    def poll(cls, context):
        return True
    def draw(self, context):
        self.layout.label(text="Little Monkey")

class TEST_PT_4(bpy.types.Panel):
    bl_label = "Pc Panel"
    def draw(self, context):
        self.layout.label(text="Foo label")

#your plugin main register/unregister

def register():

    #we first register the plugin classes (order matter)
    # ...
    # for cls in classes:
    #     bpy.utils.register_class(cls)

    # register your custom icon. might be best to use your own function.
    global ICONS
    ICONS = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__))
    ICONS.load('myicon', os.path.join(icons_dir, "myicon.png"), 'IMAGE')

    #then we initialize the module
    customtab.register()

    #then append our custom tabs!!!

    customtab.append_tab(
        uniqueid='MONKEYTAB',
        group='MYADDONGROUP1', #groups are used for spacing between tabs.
        icon='MONKEY', 
        name="Monkey!",
        description="This is a Monkey",
        panels=(TEST_PT_3,TEST_PT_3child,), #pass panels
        )

    #it's possible to define a custom poll for our tab.

    def custom_poll(context):
        active = context.active_object
        return active and "Foo" in active.name

    customtab.append_tab(
        uniqueid='MYFOOTAB',
        group='MYADDONGROUP1',
        icon='SYSTEM', 
        poll=custom_poll, 
        panels=(TEST_PT_4,),
        )

    # you can also draw a custom layout for your tab, (if you don't like registering panels)

    def custom_draw(layout,context):
        # NOTE it is advised to stick to blender ui styling! don't create a mess in there!
        layout.separator(type='LINE')
        for i,(h,c) in enumerate([("Parameters","Do this"),("Options","Do That"),("Foo","Do Foo")]):
            header, panel = layout.panel(f"mypanels{i}", default_closed=False,)
            header.label(text=h,)
            if (panel):
                panel.label(text=c)
        return None

    customtab.append_tab(
        uniqueid='CUSTOMLAYOUT',
        group='OBJECT',
        name="Custom Layout",
        icon='FUND',
        draw=custom_draw,
        )

    #it's possible to define a custom header for our tab.

    def header_drawing(layout,context):
        row = layout.row()
        row_left = row.row(align=True)
        row_left.alignment = 'LEFT'

        row_right = row.row(align=True)
        row_right.alignment = 'RIGHT'
        row_left.label(text='My Custom header!', icon_value=ICONS['myicon'].icon_id)
        row_left.label(text='', icon='RIGHTARROW')
        row_left.label(text='Data',)

        row_right.operator('mesh.primitive_plane_add', text='', icon='ADD')
        return None

    customtab.append_tab(
        uniqueid='SCARYGHOST',
        group='TOOLS', #we can also choose an existing group in ('TOOLS','SCENE','COLLECTION','OBJECT','TEXTURE',)
        icon=ICONS['myicon'].icon_id, #the 'icon' arguments accepts either a str icon identifier, or an int icon id.
        header=header_drawing,
        panels=(TEST_PT_1,TEST_PT_2,),
        )

    return None


def unregister():

    #we de-initialize our module first (order matter)
    customtab.unregister()
    
    # unregister your custom icon.. advised to use your own function.
    global ICONS
    bpy.utils.previews.remove(ICONS)

    # then we unregister our plugin 
    # ...
    # for cls in reversed(classes):
    #     bpy.utils.unregister_class(cls)

    return None
