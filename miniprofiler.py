# %%

from copy import deepcopy
import json
import psutil
from IPython.core.getipython import get_ipython
from IPython.core.interactiveshell import ExecutionInfo, ExecutionResult, InteractiveShell
from IPython.display import JSON, display
from pyinstrument import Profiler
from pyinstrument.renderers.jsonrenderer import JSONRenderer
from IPython.core.magic import register_cell_magic


class MiniProf:
    ip: InteractiveShell
    profiler: Profiler

    def __init__(self, ip: InteractiveShell):
        self.ip = ip
        self.memory_usage = {}

        self.profiler = Profiler(async_mode="enabled")

    def register(self, ip: InteractiveShell):
        ip.events.register("pre_run_cell", self.pre_run_hook)
        ip.events.register("post_run_cell", self.post_run_hook)

    def unregister(self, ip: InteractiveShell):
        ip.events.unregister("pre_run_cell", self.pre_run_hook)
        ip.events.unregister("post_run_cell", self.post_run_hook)

    def pre_run_hook(self, info: ExecutionInfo):
        cell_id = info.cell_id
        self.memory_usage[cell_id] = psutil.Process().memory_info().rss
        self.profiler.start()

    def post_run_hook(self, result: ExecutionResult):
        if result.info is None:
            return

        if result.info is None or result.info.cell_id not in self.memory_usage:
            # When running this module directly in a notebook, the post run hook may be called when we haven't started profiling yet
            return

        cell_id = result.info.cell_id
        
        self.profiler.stop()

        profile = self.profiler.output(renderer=JSONRenderer(show_all=False))

        profile = json.loads(profile)
        # trim first two children
        root_frame = deepcopy(profile["root_frame"])
        profile["root_frame"] = root_frame["children"][0]["children"][0]

        end_memory = psutil.Process().memory_info().rss
        start_memory = self.memory_usage.pop(cell_id, 0)
        memory_diff = end_memory - start_memory

        profile['memory_usage'] = memory_diff / 1024 / 1024

        # For demonstration, here's the raw JSON profiling and memory usage
        display(JSON(profile))

        # On the jupyterlab extension we can pick up when we get a special media type for this output
        # and render it in a more useful way. As far as I know, there isn't a way to set this as metadata
        # on the notebook.
        display({
            "application/vnd.miniprof+json": profile
        }, raw=True)
        print("anonymous trace sent to anaconda")

        # An alternative here would be to decorate metadata on the execute reply


# %%

def load_ipython_extension(ipython):
    profiler = MiniProf(ipython)
    profiler.register(ipython)
    ipython.user_ns["mini_prof"] = profiler

# For interactive testing in the notebook
# load_ipython_extension(get_ipython())


# @register_cell_magic
# def profile(line, cell):
#     load_ipython_extension(get_ipython())
