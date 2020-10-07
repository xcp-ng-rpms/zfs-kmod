# XCP-ng notice: this spec file and the associated source come from
# the zfs-kmod source RPM created out of the zfs upstream build scripts.
# The 'upstream' branch of this repository contains the unmodified
# spec file and sources from that source RPM.
# See our zfs.spec for detailed steps.

%define module  zfs

# See comment in zfs.spec.in.
%global __brp_mangle_shebangs_exclude_from arc_summary.py|arcstat.py|dbufstat.py|test-runner.py|zts-report.py

%if !%{defined ksrc}
%if 0%{?rhel}%{?fedora}
%define ksrc    ${kernel_version##*___}
%else
%define ksrc    "$( \
        if [ -e "/usr/src/linux-${kernel_version%%___*}" ]; then \
            echo "/usr/src/linux-${kernel_version%%___*}"; \
        elif [ -e "/lib/modules/${kernel_version%%___*}/source" ]; then \
            echo "/lib/modules/${kernel_version%%___*}/source"; \
        else \
            echo "/lib/modules/${kernel_version%%___*}/build"; \
        fi)"
%endif
%endif

%if !%{defined kobj}
%if 0%{?rhel}%{?fedora}
%define kobj    ${kernel_version##*___}
%else
%define kobj    "$( \
        if [ -e "/usr/src/linux-${kernel_version%%___*}" ]; then \
            echo "/usr/src/linux-${kernel_version%%___*}"; \
        else \
            echo "/lib/modules/${kernel_version%%___*}/build"; \
        fi)"
%endif
%endif

#define repo    rpmfusion
#define repo    chaos

# (un)define the next line to either build for the newest or all current kernels
%define buildforkernels newest
#define buildforkernels current
#define buildforkernels akmod

%bcond_with     debug
%bcond_with     debuginfo


Name:           %{module}-kmod

Version:        0.8.5
Release:        1%{?dist}
Summary:        Kernel module(s)

Group:          System Environment/Kernel
License:        CDDL
URL:            http://zfsonlinux.org/
Source0:        %{module}-%{version}.tar.gz
Source10:       kmodtool
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id} -u -n)
%if 0%{?rhel}%{?fedora}
BuildRequires:  gcc, make
BuildRequires:  elfutils-libelf-devel
%endif

# The developments headers will conflict with the dkms packages.
Conflicts:      %{module}-dkms


# XCP-ng: kernel detection simplified to adapt to XS kernel directory structure and naming
BuildRequires: kernel-devel
%if !%{defined kernels}
    %define kernels %(ls -1 /lib/modules)
%endif
# End of XCP-ng specific section


# LDFLAGS are not sanitized by arch/*/Makefile for these architectures.
%ifarch ppc ppc64 ppc64le aarch64
%global __global_ldflags %{nil}
%endif

%if 0%{?fedora} >= 17
%define prefix  /usr
%endif

# Kmodtool does its magic here.  A patched version of kmodtool is shipped
# with the source rpm until kmod development packages are supported upstream.
# https://bugzilla.rpmfusion.org/show_bug.cgi?id=2714
%{expand:%(bash %{SOURCE10} --target %{_target_cpu} %{?repo:--repo %{?repo}} --kmodname %{name} %{?buildforkernels:--%{buildforkernels}} --devel %{?prefix:--prefix "%{?prefix}"} %{?kernels:--for-kernels "%{?kernels}"} %{?kernelbuildroot:--buildroot "%{?kernelbuildroot}"} --obsolete-name spl --obsolete-version 0.8 2>/dev/null) }


%description
This package contains the ZFS kernel modules.

%prep
# Error out if there was something wrong with kmodtool.
%{?kmodtool_check}

# Print kmodtool output for debugging purposes:
bash %{SOURCE10}  --target %{_target_cpu} %{?repo:--repo %{?repo}} --kmodname %{name} %{?buildforkernels:--%{buildforkernels}} --devel %{?prefix:--prefix "%{?prefix}"} %{?kernels:--for-kernels "%{?kernels}"} %{?kernelbuildroot:--buildroot "%{?kernelbuildroot}"} --obsolete-name spl --obsolete-version 0.8 2>/dev/null

%if %{with debug}
    %define debug --enable-debug
%else
    %define debug --disable-debug
%endif

%if %{with debuginfo}
    %define debuginfo --enable-debuginfo
%else
    %define debuginfo --disable-debuginfo
%endif

# Leverage VPATH from configure to avoid making multiple copies.
%define _configure ../%{module}-%{version}/configure

%setup -q -c -T -a 0

for kernel_version in %{?kernel_versions}; do
    %{__mkdir} _kmod_build_${kernel_version%%___*}
done

%build
for kernel_version in %{?kernel_versions}; do
    cd _kmod_build_${kernel_version%%___*}
    %configure \
        --with-config=kernel \
        --with-linux=%{ksrc} \
        --with-linux-obj=%{kobj} \
        %{debug} \
        %{debuginfo}
    make %{?_smp_mflags}
    cd ..
done


%install
rm -rf ${RPM_BUILD_ROOT}

# Relies on the kernel 'modules_install' make target.
for kernel_version in %{?kernel_versions}; do
    cd _kmod_build_${kernel_version%%___*}
    make install \
        DESTDIR=${RPM_BUILD_ROOT} \
        %{?prefix:INSTALL_MOD_PATH=%{?prefix}} \
        INSTALL_MOD_DIR=%{kmodinstdir_postfix}
    cd ..
done
# find-debuginfo.sh only considers executables
chmod u+x ${RPM_BUILD_ROOT}%{kmodinstdir_prefix}/*/extra/*/*/*
%{?akmod_install}


%clean
rm -rf $RPM_BUILD_ROOT
