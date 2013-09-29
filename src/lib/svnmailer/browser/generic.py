# -*- coding: iso-8859-1 -*-
# pylint-version = 0.7.0
#
# Copyright 2005 André Malo or his licensors, as applicable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Generic repository browser URL construction
"""
__author__    = "André Malo"
__docformat__ = "restructuredtext en"
__all__       = ['Generator']

# global imports
from svnmailer.browser import _base


class Generator(_base.BaseGenerator):
    """ Generic URL generator """

    def _createTemplate(self, base_url, config):
        """ Returns generic templates from the config """
        base_url # pylint

        return _base.Template(
            revision = config.revision_url,
            deleted  = config.diff_delete_url,
            copied   = config.diff_copy_url,
            added    = config.diff_add_url,
            modified = config.diff_modify_url,
        )
