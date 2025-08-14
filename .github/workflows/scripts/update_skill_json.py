# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc. and Oscillate Labs LLC
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# Mike Gray
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
from os.path import expanduser, isdir, join, isfile
from pprint import pprint
from shutil import copy, move
from sys import argv


def get_skill_json(skill_dir: str, lang_code: str = "en-us"):
    print(f"skill_dir={skill_dir}")
    skill_json = join(skill_dir, f"skill_homeassistant/locale/{lang_code}/skill.json")
    skill_spec = get_poetry_skill_data(skill_dir, lang_code)
    pprint(skill_spec)
    try:
        with open(skill_json) as f:
            current = json.load(f)
    except Exception as e:
        print(e)
        current = None
    if current != skill_spec:
        print("Skill updated. Writing skill.json")
        with open(skill_json, "w+") as f:
            json.dump(skill_spec, f, indent=4)
    else:
        print("No changes to skill.json")
    move(skill_json, skill_json)


def get_poetry_skill_data(skill_dir: str, lang_code: str = "en-us"):
    skill_data = {
        "skill_id": "skill_homeassistant.oscillatelabsllc",
        "source": "https://github.com/oscillatelabsllc/skill-homeassistant",
        "package_name": "skill-homeassistant",
        "pip_spec": "skill-homeassistant",
        "license": "Apache-2.0",
        "author": ["Mike Gray <mike@oscillatelabs.net>"],
        "icon": "https://www.home-assistant.io/images/home-assistant-logo.svg",
        "images": [],
        "name": "skill-homeassistant",
        "description": "Unified OpenVoiceOS/Neon.AI skill for Home Assistant",
        "examples": [],
        "tags": ["ovos", "neon", "homeassistant"],
        "version": "",
    }
    from toml import load

    skill_dir = expanduser(skill_dir)
    if not isdir(skill_dir):
        raise FileNotFoundError(f"Not a Directory: {skill_dir}")
    pyproject = join(skill_dir, "pyproject.toml")
    if not isfile(pyproject):
        raise FileNotFoundError(f"Not a Directory: {pyproject}")
    with open(pyproject) as f:
        data = load(f)
    skill_data["package_name"] = data["tool"]["poetry"].get("name", "Unknown")
    skill_data["name"] = data["tool"]["poetry"].get("name", "Unknown")
    skill_data["description"] = data["tool"]["poetry"].get("name", "description")
    skill_data["pip_spec"] = data["tool"]["poetry"].get("name", "Unknown")
    skill_data["license"] = data["tool"]["poetry"].get("license", "Unknown")
    skill_data["author"] = data["tool"]["poetry"].get("authors", [""])
    skill_data["tags"] = data["tool"]["poetry"].get("keywords", ["ovos", "neon", "homeassistant"])
    skill_data["version"] = data["tool"]["poetry"].get("version", [""])

    with open(join(skill_dir, f"skill_homeassistant/locale/{lang_code}/skill.json"), encoding="utf-8") as f:
        skill_json = json.load(f)
        skill_data["examples"] = skill_json.get("examples", [])
    return skill_data


if __name__ == "__main__":
    supported_langs = ["en-us", "pl-pl"]
    for lang in supported_langs:
        get_skill_json(argv[1], lang_code=lang)
    copy("skill_homeassistant/locale/en-us/skill.json", "skill.json")
