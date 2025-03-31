# SPDX-FileCopyrightText: 2025 BD3D DIGITAL DESIGN (Dorian B.)
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from . import customtab

# NOTE this file is an implementation example 
# see how the customtab module is used. 
# implement your own panels and plugin structure.

# Example of panels

class TEST_PT_1(bpy.types.Panel):
    bl_label = "My custom curve"
    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'CURVE')
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
        #NOTE best to use context.active_object instead of context.object in the Properties editor.
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
        row_left.label(text='My Custom header!', icon='GHOST_ENABLED')
        row_left.label(text='', icon='RIGHTARROW')
        row_left.label(text='Data',)

        row_right.operator('mesh.primitive_plane_add', text='', icon='ADD')
        return None

    customtab.append_tab(
        uniqueid='SCARYGHOST',
        group='TOOLS', #we can also choose an existing group in ('TOOLS','SCENE','COLLECTION','OBJECT','TEXTURE',)
        icon='GHOST_ENABLED',
        header=header_drawing,
        panels=(TEST_PT_1,TEST_PT_2,),
        )

    return None


def unregister():

    #we de-initialize our module first (order matter)
    customtab.unregister()

    # then we unregister our plugin 
    # ...
    # for cls in reversed(classes):
    #     bpy.utils.unregister_class(cls)

    return None
