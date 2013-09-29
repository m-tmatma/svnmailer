#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys

PACKAGES = [
    "svnmailer",
    "svnmailer.browser",
    "svnmailer.notifier",
    "svnmailer.settings",
]
SCRIPTS = ["src/svn-mailer"]
DOCS = [ # plus files added dynamically from docs/*
    "CHANGES",
    "CREDITS",
    "LICENSE",
    "NOTICE",
    "PKG-INFO",
    "README",
]
MAN = {
    "1": ["docs/svn-mailer.1"]
}
APIDOCDIRS = [ # expected under docs/; files are collected automatically
    "apidoc",
    "apidoc/private",
    "apidoc/public",
]
SAMPLES = [
    "sample/README",         # must be the first
    "sample/advanced.conf",
    "sample/authors.txt",
    "sample/groups.conf",
    "sample/passwords.txt",
    "sample/simple.conf",
]
HOOKS = [
    'sample/hooks/post-commit',
    'sample/hooks/post-lock',
    'sample/hooks/post-revprop-change',
    'sample/hooks/post-unlock',
]

def check_versions():
    major, minor = sys.version_info[:2]
    if major < 2 or minor < 3:
        raise AssertionError(
            "Python 2.3 or later required, but sys.version_info = %r" %
            (sys.version_info, )
        )

    try:
        import svn
    except:
        print >> sys.stderr, \
            "WARNING: Subversion/Python bindings could not be imported"


def setup():
    check_versions()

    import posixpath, re
    from distutils import core, file_util, filelist, util
    from distutils.command import build_scripts as _build_scripts
    from distutils.command import install as _install
    from distutils.command import install_data as _install_data
    from distutils.command import install_scripts as _install_scripts
    win32 = sys.platform == 'win32'
    store = {}

    def fixfiles(files, ext = 'txt', fill = None):
        newfiles = []
        if store.get('no-replace', False):
            fill = None

        for name in files:
            if win32 and ext and '.' not in posixpath.basename(name):
                newname = "%s.%s" % (name, ext)
            else:
                newname = name

            newfiles.append(newname)
            newpath = util.convert_path(newname)
            path = util.convert_path(name)
            content = [line.rstrip() for line in file(path)]
            if fill is not None:
                newcont = []
                for line in content:
                    for key, value in fill.items():
                        line = line.replace("@@%s@@" % key, value)
                    newcont.append(line)
                content = newcont

            file_util.write_file(newpath, content)

        return newfiles


    # buggy distutils. anchor patterns don't work on non-unices -> create
    # regexps by ourselves. This function converts slashes to
    # re.escape(os.path.sep) and adds anchors to both sides
    def convre(pattern):
        return "^%s$" % re.escape(os.path.sep).join(pattern.split('/'))


    class build_scripts(_build_scripts.build_scripts):
        def finalize_options(self):
            _build_scripts.build_scripts.finalize_options(self)
            self.distribution.scripts = self.scripts = \
                fixfiles(SCRIPTS, ext = 'py')
            

    class install(_install.install):
        user_options = _install.install.user_options + [
            ('no-install-docs', None,
             "do not install the documentation files and samples"),
            ('no-replace', None,
             "do not replace the placeholders in the sample files"),
        ]
        boolean_options = _install.install.boolean_options + [
            'no-install-docs',
            'no-replace',
        ]

        def initialize_options(self):
            _install.install.initialize_options(self)
            self.no_install_docs = 0
            self.no_replace = 0

        def finalize_options(self):
            _install.install.finalize_options(self)
            if self.no_install_docs:
                store['no-install-docs'] = True
            if self.no_replace:
                store['no-replace'] = True


    class install_scripts(_install_scripts.install_scripts):
        def finalize_options(self):
            _install_scripts.install_scripts.finalize_options(self)
            store['scripts'] = self.install_dir
            self.distribution.scripts = self.scripts = \
                fixfiles(SCRIPTS, ext = 'py')

        def get_inputs(self):
            return self.scripts


    class install_data(_install_data.install_data):
        def finalize_options(self):
            _install_data.install_data.finalize_options(self)
            store['data'] = self.install_dir
            self.data_files = []

            docs = fixfiles(DOCS)
            moredocs = filelist.FileList()
            moredocs.findall('docs')
            moredocs.include_pattern(convre(r"docs/[^/]+"), is_regex = 1)
            moredocs.exclude_pattern(convre(r"docs/[^/]+.\d"), is_regex = 1)
            docs.extend(moredocs.files)
            base = 'doc/svnmailer'
            self.data_files.append((base, docs))

            rre = re.escape('/') == '\\/'
            for path in APIDOCDIRS:
                matchpath = "docs/%s" % path
                repath = re.escape(matchpath)
                if rre:
                    repath = repath.replace('\\/', '/')
                apidocs = filelist.FileList()
                apidocs.findall(util.convert_path(matchpath))
                apidocs.include_pattern(
                    convre('%s/[^/]+' % repath), is_regex = 1
                )
                base = 'doc/svnmailer/%s'% path
                self.data_files.append((base, apidocs.files))

            samples = fixfiles(SAMPLES)
            base = 'doc/svnmailer/sample'
            self.data_files.append((base, samples))

            hooks = HOOKS
            base = 'doc/svnmailer/sample/hooks'
            if win32:
                hooks = ["%s.bat" % hook for hook in hooks]
                scriptsdefault = "C:\\path\\to"
            else:
                scriptsdefault = "/usr/bin"
            hooks = fixfiles(hooks, fill = {
                'PYTHON': sys.executable,
                'SCRIPTS': store.get('scripts', scriptsdefault),
            })
            self.data_files.append((base, hooks))

            # man pages only on *x
            if not win32:
                for section, pages in MAN.items():
                    fixfiles(pages)
                    self.data_files.append(("man/man%s" % section, pages))

            # so late, because some files need to be touched in the tree
            # anyway
            if store.get('no-install-docs', False):
                self.data_files = []


    core.setup(
        name = "svnmailer",
        version = "1.1.0-dev-r1373",
        description = "Feature rich subversion commit notification tool",
        author = "André Malo",
        author_email = "nd@perlig.de",
        url = "http://opensource.perlig.de/svnmailer/",
        license = "Apache License 2.0",

        package_dir = {'': 'src/lib'},
        packages = PACKAGES,
        scripts = ['dummy'], # see install_scripts above
        data_files = ['dummy'], # see install_data above
        cmdclass = {
            'install'        : install,
            'install_data'   : install_data,
            'build_scripts'  : build_scripts,
            'install_scripts': install_scripts,
        }
    )


########### main ############
if __name__ == '__main__':
    setup()
