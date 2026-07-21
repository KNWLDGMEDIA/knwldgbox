from functools import cache
import importlib
import ast
import os

class routerClass_:

    def file_class(self, list_py_file, exclude_list, exclude_argument = ["eval","exec","compile","os.system","os.popen","subprocess.run","pickle.load()","pickle.loads()","yaml.load()","marshal.load()","marshal.loads()","shelve.open"]):
        file_with_class = []
        sub_file = []
        for one_py_file in list_py_file:
            authorize = True
            handle = open(one_py_file,encoding="utf-8")
            tree_file = ast.parse(handle.read())
            for node in ast.walk(tree_file):
                    if isinstance(node, ast.ClassDef):
                        sub_file = [one_py_file, node.name]
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id  in set(exclude_argument):
                                authorize = False
            if authorize == True and len(sub_file) == 2:
                file_with_class.append(sub_file)
            handle.close()
        return file_with_class

    def scandir_and_sort(self, dict_stack,file, exclude_list):
        for one_content in os.scandir(file):
            array_name_content = (one_content.name).split(".")
            if one_content.name not in exclude_list:
                if array_name_content[-1] == "py":
                    dict_stack["file_python"].append(one_content.path)
                if one_content.is_dir() == True:
                    dict_stack["dir"].append(one_content.path)
        return dict_stack

    def configure_class(self, file_py_with_class, start_dir):
        dict_class = {}
        for one_class in file_py_with_class:
            name_file = one_class[0].split(".")[0].replace("/","\\").split("\\")
            name_class = one_class[1]
            if_construct = False
            construct_module =  ""
            for one_module in name_file:
                if  if_construct == True:
                    construct_module = construct_module + f"{one_module}."
                if start_dir == one_module:
                    if_construct = True
            if len(construct_module) >=4:
                dict_class[name_class] = getattr(importlib.import_module(construct_module[:-1]), name_class)
        return dict_class

    @cache
    def pipe_router_class(self, start_dir = "routerClass", start_file =  os.getcwd(), exclude_list = [".git","__pycache__","venv", ".venv","main.py"], depth = 10):
        dict_stack = {"file_python" : [], "dir" : [start_file]}
        already_seen = []
        tick = 0
        for x in range(depth):
            for one_path_dir in dict_stack["dir"]:
                if one_path_dir not in set(already_seen):
                    start_file = one_path_dir
                    tick += 1
                    dict_stack = self.scandir_and_sort(dict_stack,start_file,set(exclude_list)).copy()
                    already_seen.append(one_path_dir)
        
        file_py_with_class = self.file_class(dict_stack["file_python"],exclude_list)
        return self.configure_class(file_py_with_class, start_dir)
        

    def __init__(self):
        pass