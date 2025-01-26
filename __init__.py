bl_info = {
    "name": "GPT4Blender",
    "author": "tintwotin",
    "description": "Integrates the GPT4All model into Blender Text Editor",
    "blender": (3, 0, 0),
    "version": (0, 0, 1),
    "location": "Text Editor > GPT4All",
    "warning": "",
    "category": "Text Editor",
}

import bpy
import aud
import textwrap
import re
import os
import subprocess
import platform
import site
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, PointerProperty, IntProperty
from bpy.types import Operator, AddonPreferences, Panel, PropertyGroup

# Only GPU is supported, but can be changed:
# model = GPT4All(model, device="gpu")  # , device='gpu') # device='amd', device='intel'


def isWindows():
    return os.name == "nt"


def isMacOS():
    return os.name == "posix" and platform.system() == "Darwin"


def isLinux():
    return os.name == "posix" and platform.system() == "Linux"


def python_exec():
    import sys

    if isWindows():
        return os.path.join(sys.prefix, "bin", "python.exe")
    elif isMacOS():
        try:
            # 2.92 and older
            path = bpy.app.binary_path_python
        except AttributeError:
            # 2.93 and later
            import sys

            path = sys.executable
        return os.path.abspath(path)
    elif isLinux():
        return os.path.join(sys.prefix, "bin", "python")
    else:
        print("Sorry, still not implemented for ", os.name, " - ", platform.system)


def import_module(module, install_module):
    module = str(module)
    python_exe = python_exec()
    try:
        subprocess.call([python_exe, "-m", "ensurepip"])
        subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    except ImportError:
        pass
    try:
        subprocess.call([python_exe, "import ", packageName])
    except:
        print("\nInstalling: " + module + " module")
        subprocess.call([python_exe, "-m", "pip", "install", install_module, "--no-warn-script-location", "--upgrade"])

        try:
            exec("import " + module)
        except ModuleNotFoundError:
            return False
    return True


# Function to check and install GPT4All
def ensure_gpt4all_installed():
    module = "gpt4all"

    try:
        from gpt4all import GPT4All

        print("Checking: GPT4ALL is installed.")
    except Exception as e:
        print(f"{e}")
        import_module(module, "gpt4all[cuda]")
        # get_supported_models()
        return []


def get_module_dependencies(module_name):
    """
    Get the list of dependencies for a given module.
    """
    pybin = python_exec()
    result = subprocess.run([pybin, "-m", "pip", "show", module_name], capture_output=True, text=True)
    output = result.stdout.strip()
    dependencies = []
    for line in output.split("\n"):
        if line.startswith("Requires:"):
            dependencies = line.split(":")[1].strip().split(", ")
            break
    return dependencies


def uninstall_module_with_dependencies(module_name):
    """
    Uninstall a module and its dependencies.
    """
    pybin = python_exec()
    dependencies = get_module_dependencies(module_name)
    # Uninstall the module
    subprocess.run([pybin, "-m", "pip", "uninstall", "-y", module_name])
    # Uninstall the dependencies
    for dependency in dependencies:
        print("\n ")
        if len(dependency) > 5 and str(dependency[5].lower) != "numpy":
            subprocess.run([pybin, "-m", "pip", "uninstall", "-y", dependency])


#def get_supported_models():
#    ensure_gpt4all_installed()  # Ensure gpt4all is installed
#    try:
#        from gpt4all import GPT4All

#        gpt4all = GPT4All()
#        models = gpt4all.list_models()
#        print(models)
#        #        supported_models = [(model, model, f"Use {model} model") for model in models]
#        #        print("Supported models:", supported_models)

#        return models
#    except Exception as e:
#        print(f"Error retrieving supported models: {e}")
#        return []


class GPT4AllAddonPreferences(AddonPreferences):
    bl_idname = __name__

    soundselect: EnumProperty(
        name="Sound",
        items={
            ("ding", "Ding", "A simple bell sound"),
            ("coin", "Coin", "A Mario-like coin sound"),
            ("user", "User", "Load a custom sound file"),
        },
        default="ding",
    )

    usersound: StringProperty(
        name="User",
        description="Load a custom sound from your computer",
        subtype="FILE_PATH",
        default="",
        maxlen=1024,
    )

    playsound: BoolProperty(
        name="Audio Notification",
        default=True,
    )

    model_select: EnumProperty(
        name="Model",
        items={
            (
                "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
                "Nous-Hermes-2-Mistral-7B-DPO.Q4_0 8 GB",
                "https://huggingface.co/NousResearch/Nous-Hermes-2-Mistral-7B-DPO-GGUF/resolve/main/Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
            ),
            (
                "qwen2.5-coder-7b-instruct-q4_0.gguf",
                "Qwen2.5 Coder 7b Instruct Q4 8 GB",
                "https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_0.gguf",
            ),
            (
                "Meta-Llama-3-8B-Instruct.Q4_0.gguf",
                "Meta-Llama-3-8B-Instruct.Q4_0 8 GB",
                "https://gpt4all.io/models/gguf/Meta-Llama-3-8B-Instruct.Q4_0.gguf",
            ),
            (
                "mistral-7b-instruct-v0.1.Q4_0.gguf",
                "mistral-7b-instruct-v0.1.Q4_0 8 GB",
                "https://gpt4all.io/models/gguf/mistral-7b-instruct-v0.1.Q4_0.gguf",
            ),
            (
                "mistral-7b-openorca.gguf2.Q4_0.gguf",
                "mistral-7b-openorca.gguf2.Q4_0 8 GB",
                "https://gpt4all.io/models/gguf/mistral-7b-openorca.gguf2.Q4_0.gguf",
            ),
            (
                "gpt4all-falcon-newbpe-q4_0.gguf",
                "gpt4all-falcon-newbpe-q4_0 8 GB",
                "https://gpt4all.io/models/gguf/gpt4all-falcon-newbpe-q4_0.gguf",
            ),
            ("orca-2-7b.Q4_0.gguf", "orca-2-7b.Q4_0 8 GB", "https://gpt4all.io/models/gguf/orca-2-7b.Q4_0.gguf"),
            ("orca-2-13b.Q4_0.gguf", "orca-2-13b.Q4_0 16 GB", "https://gpt4all.io/models/gguf/orca-2-13b.Q4_0.gguf"),
            (
                "wizardlm-13b-v1.2.Q4_0.gguf",
                "wizardlm-13b-v1.2.Q4_0 16 GB",
                "https://gpt4all.io/models/gguf/wizardlm-13b-v1.2.Q4_0.gguf",
            ),
            (
                "ghost-7b-v0.9.1-Q4_0.gguf",
                "ghost-7b-v0.9.1-Q4_0 8 GB",
                "https://huggingface.co/lamhieu/ghost-7b-v0.9.1-gguf/resolve/main/ghost-7b-v0.9.1-Q4_0.gguf",
            ),
            (
                "nous-hermes-llama2-13b.Q4_0.gguf",
                "nous-hermes-llama2-13b.Q4_0 16 GB",
                "https://gpt4all.io/models/gguf/nous-hermes-llama2-13b.Q4_0.gguf",
            ),
            (
                "gpt4all-13b-snoozy-q4_0.gguf",
                "gpt4all-13b-snoozy-q4_0 16 GB",
                "https://gpt4all.io/models/gguf/gpt4all-13b-snoozy-q4_0.gguf",
            ),
            (
                "mpt-7b-chat.gguf4.Q4_0.gguf",
                "mpt-7b-chat.gguf4.Q4_0 8 GB",
                "https://gpt4all.io/models/gguf/mpt-7b-chat.gguf4.Q4_0.gguf",
            ),
#            (
#                "Phi-3-mini-4k-instruct.Q4_0.gguf",
#                "Phi-3-mini-4k-instruct.Q4_0 4 GB",
#                "https://gpt4all.io/models/gguf/Phi-3-mini-4k-instruct.Q4_0.gguf",
#            ),
#            (
#                "orca-mini-3b-gguf2-q4_0.gguf",
#                "orca-mini-3b-gguf2-q4_0 4 GB",
#                "https://gpt4all.io/models/gguf/orca-mini-3b-gguf2-q4_0.gguf",
#            ),
#            (
#                "replit-code-v1_5-3b-newbpe-q4_0.gguf",
#                "replit-code-v1_5-3b-newbpe-q4_0 4 GB",
#                "https://gpt4all.io/models/gguf/replit-code-v1_5-3b-newbpe-q4_0.gguf",
#            ),
#            (
#                "starcoder-newbpe-q4_0.gguf",
#                "starcoder-newbpe-q4_0 4 GB",
#                "https://gpt4all.io/models/gguf/starcoder-newbpe-q4_0.gguf",
#            ),
            (
                "rift-coder-v0-7b-q4_0.gguf",
                "rift-coder-v0-7b-q4_0 8 GB",
                "https://gpt4all.io/models/gguf/rift-coder-v0-7b-q4_0.gguf",
            ),
#            (
#                "all-MiniLM-L6-v2.gguf2.f16.gguf",
#                "all-MiniLM-L6-v2.gguf2.f16 1 GB",
#                "https://gpt4all.io/models/gguf/all-MiniLM-L6-v2.gguf2.f16.gguf",
#            ),
            (
                "em_german_mistral_v01.Q4_0.gguf",
                "em_german_mistral_v01.Q4_0 8 GB",
                "https://huggingface.co/TheBloke/em_german_mistral_v01-GGUF/resolve/main/em_german_mistral_v01.Q4_0.gguf",
            ),
#            (
#                "nomic-embed-text-v1.f16.gguf",
#                "nomic-embed-text-v1.f16 1 GB",
#                "https://gpt4all.io/models/gguf/nomic-embed-text-v1.f16.gguf",
#            ),
#            (
#                "nomic-embed-text-v1.5.f16.gguf",
#                "nomic-embed-text-v1.5.f16 1 GB",
#                "https://gpt4all.io/models/gguf/nomic-embed-text-v1.5.f16.gguf",
#            ),
        },
        default="Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf",
    )

    tokens: IntProperty(
        name="Max Tokens",
        default=2000,
    )

    device_select: EnumProperty(
        name="Device",
        items={
            ("cpu", "CPU", "Model will run on the central processing unit"),
            ("gpu", "GPU", "Use Metal on ARM64 macOS, otherwise the same as 'kompute'"),
            ("kompute", "Kompute", "Use the best GPU provided by the Kompute backend"),
            ("cuda", "CUDA", "Use the best GPU provided by the CUDA backend"),
            ("amd", "AMD", "Use the best GPU provided by the Kompute backend from this vendor"),
            ("nvidia", "NVIDIA", "Use the best GPU provided by the Kompute backend from this vendor"),
        },
        default="cuda",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "model_select")
        layout.prop(self, "device_select")
        layout.prop(self, "tokens")

        row = layout.row()
        row.operator("gpt4all.install_dependencies", text="Install Dependencies")
        row.operator("gpt4all.uninstall_dependencies", text="Uninstall Dependencies")

        box = layout.box()
        box.prop(self, "playsound")
        row = box.row()
        row.prop(self, "soundselect")
        if self.soundselect == "user":
            row.prop(self, "usersound", text="")
        row.operator("renderreminder.gpt_play_notification", text="", icon="PLAY")
        row.active = self.playsound


class GPT_OT_sound_notification(Operator):
    """Test your notification settings"""

    bl_idname = "renderreminder.gpt_play_notification"
    bl_label = "Test Notification"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        preferences = context.preferences
        addon_prefs = preferences.addons[__name__].preferences
        if addon_prefs.playsound:
            device = aud.Device()

            def coin_sound():
                sound = aud.Sound("")
                handle = device.play(
                    sound.triangle(1000).highpass(20).lowpass(2000).ADSR(0, 0.5, 1, 0).fadeout(0.1, 0.1).limit(0, 1)
                )

                handle = device.play(
                    sound.triangle(1500).highpass(20).lowpass(2000).ADSR(0, 0.5, 1, 0).fadeout(0.2, 0.2).delay(0.1).limit(0, 1)
                )

            def ding():
                sound = aud.Sound("")
                handle = device.play(
                    sound.triangle(3000).highpass(20).lowpass(1000).ADSR(0, 0.5, 1, 0).fadeout(0, 1).limit(0, 1)
                )

            if addon_prefs.soundselect == "ding":
                ding()
            elif addon_prefs.soundselect == "coin":
                coin_sound()
            elif addon_prefs.soundselect == "user" and os.path.isfile(addon_prefs.usersound):
                sound = aud.Sound(addon_prefs.usersound)
                handle = device.play(sound)
            else:
                self.report({"ERROR"}, "Custom sound file not found.")
        return {"FINISHED"}


class GPT_OT_install_dependencies(Operator):
    bl_idname = "gpt4all.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = "Install necessary dependencies for GPT4All"

    def execute(self, context):
        ensure_gpt4all_installed()
        return {"FINISHED"}


class GPT_OT_uninstall_dependencies(Operator):
    bl_idname = "gpt4all.uninstall_dependencies"
    bl_label = "Uninstall Dependencies"
    bl_description = "Uninstall GPT4All dependencies"

    def execute(self, context):
        uninstall_module_with_dependencies("GPT4ALL")
        return {"FINISHED"}


def label_multiline(context, text, parent):
    chars = int(context.region.width / 7)
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = [wrapped_line for line in text.splitlines() for wrapped_line in wrapper.wrap(text=line)]
    for text_line in text_lines:
        parent.label(text=text_line)


class ChatHistoryItem(PropertyGroup):
    input: StringProperty()
    output: StringProperty()


class GPT4AllAddonProperties(PropertyGroup):
    chat_history: CollectionProperty(type=ChatHistoryItem)
    chat_gpt_select_prefix: StringProperty(
        name="Select Prefix",
        description="Selection prefix text",
        default="Highlight text, and add prompt to rewrite it.",
        options={"TEXTEDIT_UPDATE"},
    )
    chat_gpt_prefix: StringProperty(
        name="Prefix",
        description="Prefix text",
        default="",
        options={"TEXTEDIT_UPDATE"},
    )
    chat_gpt_input: StringProperty(
        name="Input",
        description="Input text for GPT4All",
        default="",
        options={"TEXTEDIT_UPDATE"},
    )


class GPT_OT_SendMessage(Operator):
    bl_label = "Send Message"
    bl_idname = "gpt.send_message"

    def execute(self, context):
        gpt = context.scene.gpt
        try:
            output = process_message(request_answer(gpt.chat_gpt_prefix + " " + gpt.chat_gpt_input + ": "))
            item = gpt.chat_history.add()
            item.input = gpt.chat_gpt_input
            item.output = output
            bpy.ops.renderreminder.gpt_play_notification()
        except Exception as e:
            self.report({"ERROR"}, str(e))
        return {"FINISHED"}


def request_answer(text: str) -> str:
    """Request an answer from the GPT4All model"""
    ensure_gpt4all_installed()
    gpt = bpy.context.scene.gpt
    try:
        from gpt4all import GPT4All

        gpt = bpy.context.scene.gpt
        preferences = bpy.context.preferences.addons[__name__].preferences
        model = preferences.model_select
        print("Model: " + model)
        preferences = bpy.context.preferences
        addon_prefs = preferences.addons[__name__].preferences
        tokens = addon_prefs.tokens

        collected_history = " "
        if len(gpt.chat_history) > 0:
            recent_history = gpt.chat_history[-1:]
            for history_item in recent_history:
                collected_history = collected_history + str(history_item.output)
        print(collected_history)
        model = GPT4All(model, device=addon_prefs.device_select)

        text_doc = bpy.context.space_data.text
        if text_doc is None:
            text_doc = bpy.data.texts.new("Chat GPT")
            bpy.context.space_data.text = text_doc
        output = ""
        
        system_template = """You'll act as a screenwriting co-author focused on writing and enhancing scenes while adhering to these principles:
        
        0. Do not include:
            comments
            suggestions
            notes
            explanations
            markdown
            html
            code
            

        1. Format & Style:
           - Write in Fountain format for screenplays.
           - Use concise, straightforward prose with no clichés, adverbs, or literary embellishments.

        2. Narrative Techniques:
           - Prioritize "show, don't tell" by using actions to reveal emotions and traits.
           - Avoid summarizing or reflective conclusions; end scenes *in media res*.
           - Ensure each scene has a purpose, contributing to the story’s structure and character arcs.

        3. Characterization & Dialogue:
           - Craft realistic, flawed characters whose actions align with their backstories.
           - Write casual, authentic dialogue infused with subtext.

        4. Action & Description:
           - Emphasize direct, precise descriptions and sensory details for immersive world-building.
           - Use strong nouns and verbs, avoiding qualifiers or broader reflections.

        5. Structure & Themes:
           - Follow a logical, detailed progression with a clear beginning, middle, and end.
           - Develop themes through character-driven storytelling, balancing plot and emotional depth.
           
        6. Fountain formatting:
            Scene Headings start with INT, EXT, and written in CAPS.
            Action is written as normal text.
            Character names are in UPPERCASE + line break.
            Dialogue comes right after Character  + line break.
            Parentheticals are wrapped in (parentheses) + line break.
            Transitions end in TO:  + line break

        \n"""

        #system_template = "You're a screenwriter assistant. When asked to write screenplays, you use fountain screenplay formatting with no markdown. When writing dialogue, you never let characters say what they feel or want. Parenticals should only be used, if nessessary, for a single word describing how the following dialog should be delivered emotionally.\n"
        with model.chat_session(system_template, collected_history):
            for token in model.generate(text, max_tokens=tokens, streaming=True):
                output = output + token
                text_doc.write(token)
                bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        print("Input: \n" + gpt.chat_gpt_prefix + " " + gpt.chat_gpt_input + ": ")
        print("Output: \n" + output)
        return output
    except Exception as e:
        return str(e)


class GPT_OT_SendSelection(Operator):
    bl_label = "Send Selection"
    bl_idname = "gpt.send_selection"

    @classmethod
    def poll(cls, context):
        gpt = context.scene.gpt
        return gpt.chat_gpt_select_prefix != ""

    def execute(self, context):
        gpt = context.scene.gpt

        try:
            text_editor = bpy.context.space_data.text
            text_content = text_editor.region_as_string()

            output = process_message(
                request_selection_answer(
                    "Rewrite without commenting, " + gpt.chat_gpt_select_prefix + ": " + "\n" + text_content
                )
            )

            item = gpt.chat_history.add()
            item.input = gpt.chat_gpt_select_prefix
            item.output = output

            bpy.ops.renderreminder.gpt_play_notification()
        except Exception as e:
            self.report({"ERROR"}, str(e))
        return {"FINISHED"}


def request_selection_answer(text: str) -> str:
    """Request an answer from the GPT4All model"""
    ensure_gpt4all_installed()
    try:
        from gpt4all import GPT4All

        gpt = bpy.context.scene.gpt
        text_editor = bpy.context.space_data.text
        preferences = bpy.context.preferences.addons[__name__].preferences
        model = preferences.model_select
        print("Model: " + model)
        preferences = bpy.context.preferences
        addon_prefs = preferences.addons[__name__].preferences
        tokens = addon_prefs.tokens

        model = GPT4All(model, device=addon_prefs.device_select)
        system_template = gpt.chat_gpt_select_prefix + ": \n"

        text_doc = bpy.context.space_data.text
        if text_doc is None:
            text_doc = bpy.data.texts.new("Chat GPT")
            bpy.context.space_data.text = text_doc
        output = ""
        with model.chat_session(system_template):
            for token in model.generate(text, max_tokens=tokens, streaming=True):
                output = output + token
                text_doc.write(token)
                bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        print("Input: \n" + gpt.chat_gpt_select_prefix + ": " + "\n" + text_editor.region_as_string())
        print("Output: \n" + output)
        return output
    except Exception as e:
        return str(e)


class GPT_OT_RemoveChatHistoryItem(Operator):
    bl_idname = "gpt.remove_chat_history_item"
    bl_label = "Remove Chat History Item"
    bl_description = "Remove this chat history item"

    index: bpy.props.IntProperty()

    def execute(self, context):
        gpt = context.scene.gpt
        if 0 <= self.index < len(gpt.chat_history):
            gpt.chat_history.remove(self.index)
        return {"FINISHED"}


class GPT_OT_CopyChatHistoryItem(Operator):
    bl_idname = "gpt.copy_chat_history_item"
    bl_label = "Copy Chat History Item"
    bl_description = "Copy this chat history item to clipboard"

    index: bpy.props.IntProperty()

    def execute(self, context):
        gpt = context.scene.gpt
        if 0 <= self.index < len(gpt.chat_history):
            item = gpt.chat_history[self.index]
            text = f"Input:\n{item.input}\n\nOutput:\n{item.output}"
            context.window_manager.clipboard = text
        return {"FINISHED"}


class GPT_PT_MainPanel(Panel):
    bl_label = "GPT4ALL"
    bl_idname = "GPT_PT_main_panel"
    bl_space_type = "TEXT_EDITOR"
    bl_region_type = "UI"
    bl_category = "GPT4ALL"

    def draw(self, context):
        layout = self.layout
        gpt = context.scene.gpt

        layout = self.layout
        layout = layout.box()
        layout = layout.column(align=True)
        layout.label(text="Write")
        wide = layout
        wide.scale_y = 1.25
        wide.prop(gpt, "chat_gpt_prefix", text="")  # GPT_OT_SendSelection

        row = layout.row(align=True)

        row.prop(gpt, "chat_gpt_input", text="")
        row.operator("gpt.send_message", text="", icon="PLAY")

        box = layout.box()
        box = box.column(align=True)
        text = gpt.chat_gpt_prefix + "\n" + gpt.chat_gpt_input
        label_multiline(context=context, text=text, parent=box)

        layout = self.layout
        layout = layout.box()
        layout = layout.column(align=True)
        layout.label(text="Rewrite")
        row = layout.row(align=True)
        row.scale_y = 1.25
        row.prop(gpt, "chat_gpt_select_prefix", text="")
        row.operator("gpt.send_selection", text="", icon="PLAY")

        if len(gpt.chat_history) > 0:
            layout = self.layout
            layout = layout.box()
            layout = layout.column()
            recent_history = gpt.chat_history[-3:]
            layout.separator()
            layout.label(text="Chat History (Last " + str(len(recent_history)) + ")")

            for i, item in enumerate(reversed(recent_history)):
                layout.use_property_split = True
                box = layout.box()
                box = box.column(align=True)

                row = box.row(align=True)
                row.alignment = "RIGHT"
                copy_op = row.operator("gpt.copy_chat_history_item", text="", icon="COPYDOWN")
                copy_op.index = len(gpt.chat_history) - len(recent_history) + i
                op = row.operator("gpt.remove_chat_history_item", text="", icon="TRASH")
                op.index = len(gpt.chat_history) - len(recent_history) + i

                box.label(text="Input:")
                label_multiline(context, item.input, box)
                box.label(text="Output:")
                label_multiline(context, item.output, box)


def process_message(message: str) -> str:
    """Process the message to make it more readable"""
    # message = re.sub(r"[\"#/@<>{}`+=|]", "", message)
    lines = message.split("\n")
    processed = []
    in_code_block = False
    for line in lines:
        line = line.rstrip()
        if line == "```python":
            in_code_block = True
        elif in_code_block:
            if line == "```":
                in_code_block = False
            else:
                processed.append(line)
        elif line:
            words = line.split(" ")
            while len(words) > 0:
                line = ""
                while len(words) > 0:
                    line += words.pop(0) + " "
                processed.append(line.rstrip())
        else:
            processed.append("")
    return "\n".join(processed)


classes = (
    GPT_OT_sound_notification,
    GPT_OT_SendSelection,
    GPT_PT_MainPanel,
    GPT_OT_SendMessage,
    GPT_OT_install_dependencies,
    GPT_OT_uninstall_dependencies,
    ChatHistoryItem,
    GPT_OT_RemoveChatHistoryItem,
    GPT_OT_CopyChatHistoryItem,
    GPT4AllAddonProperties,
    GPT4AllAddonPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gpt = PointerProperty(type=GPT4AllAddonProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gpt


if __name__ == "__main__":
    register()
