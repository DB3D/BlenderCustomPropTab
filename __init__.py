# SPDX-FileCopyrightText: 2025 BD3D DIGITAL DESIGN (Dorian B.)
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from . import customtab


class TEST_PT_1(bpy.types.Panel):
    bl_label = "My custom curve"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_customtab = 'MYTAB_GHOST'

    @classmethod
    def poll(cls, context):
        return (context.object.type == 'CURVE')

    def draw(self, context):
        self.layout.label(text="CurveSpecial")


class TEST_PT_2(bpy.types.Panel):
    bl_label = "My custom panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_customtab = 'MYTAB_GHOST'

    def draw(self, context):
        self.layout.label(text="Prooot")


class TEST_PT_3(bpy.types.Panel):
    bl_label = "My Monkey"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_customtab = 'MYTAB_MONKEY'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        self.layout.label(text="Monkey Label")


class TEST_PT_3child(bpy.types.Panel):
    bl_label = ""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_customtab = 'MYTAB_MONKEY'
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
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_customtab = 'MYTAB_FOO'

    def draw(self, context):
        self.layout.label(text="Foo label")


classes = (
    TEST_PT_1,
    TEST_PT_2,
    TEST_PT_3,
    TEST_PT_3child,
    TEST_PT_4,
    )


def register():

    #we first register our panels (order matter)
    for cls in classes:
        bpy.utils.register_class(cls)

    #then we initialize the module
    customtab.register()

    def custom_poll_function(context):
        #NOTE best to use context.active_object instead of context.object in the Properties editor.
        active = context.active_object
        return active and "Foo" in active.name

    def custom_draw_header_function(layout,context):
        layout.label(text='Custom header!')
        layout.operator('mesh.primitive_plane_add', text='Add Plane')
        return None

    #then append our custom tabs. (No need to remove them on unreg.)
    customtab.append_tab(uniqueid="MYTAB_MONKEY", icon="MONKEY", name="Proot", description="Monkey proot",)
    customtab.append_tab(uniqueid="MYTAB_FOO", icon="SYSTEM", poll=custom_poll_function,) 
    customtab.append_tab(spacer=True)
    customtab.append_tab(uniqueid="MYTAB_GHOST", icon="GHOST_ENABLED", header=custom_draw_header_function,)

    return None


def unregister():

    #we de-initialize our module first (order matter)
    customtab.unregister()

    #then unregister our panels 
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    return None
