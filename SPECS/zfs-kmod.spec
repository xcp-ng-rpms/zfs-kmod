# XCP-ng notice: this spec file and the associated source come from
# the zfs-kmod source RPM created out of the zfs upstream build scripts.
# The 'upstream' branch of this repository contains the unmodified
# spec file and sources from that source RPM.
# See our zfs.spec for detailed steps.

%define module  zfs

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
%bcond_with     debug_dmu_tx


Name:           %{module}-kmod

Version:        0.7.13
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

BuildRequires: gcc
BuildRequires: kernel-devel

%if !%{defined kernels}
    %define kernels %(ls -1 /lib/modules)
%endif

%if 0%{?rhel}%{?fedora}%{?suse_version}
BuildRequires:             kmod-spl-devel = %{version}
# In XCP-ng we build for only one kernel at a time
BuildRequires:             kmod-spl-devel-4.19.0+1 = %{version}
%global KmodsRequires      kmod-spl
%global KmodsDevelRequires kmod-spl-devel
%global KmodsMetaRequires  spl-kmod
%endif

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
%{expand:%(bash %{SOURCE10} --target %{_target_cpu} %{?repo:--repo %{?repo}} --kmodname %{name} %{?buildforkernels:--%{buildforkernels}} --devel %{?prefix:--prefix "%{?prefix}"} %{?kernels:--for-kernels "%{?kernels}"} %{?kernelbuildroot:--buildroot "%{?kernelbuildroot}"} 2>/dev/null) }


%description
This package contains the ZFS kernel modules.

%prep
# Error out if there was something wrong with kmodtool.
%{?kmodtool_check}

# Print kmodtool output for debugging purposes:
bash %{SOURCE10}  --target %{_target_cpu} %{?repo:--repo %{?repo}} --kmodname %{name} %{?buildforkernels:--%{buildforkernels}} --devel %{?prefix:--prefix "%{?prefix}"} %{?kernels:--for-kernels "%{?kernels}"} %{?kernelbuildroot:--buildroot "%{?kernelbuildroot}"} 2>/dev/null

%if %{with debug}
    %define debug --enable-debug
%else
    %define debug --disable-debug
%endif

%if %{with debug_dmu_tx}
    %define debug_dmu_tx --enable-debug-dmu-tx
%else
    %define debug_dmu_tx --disable-debug-dmu-tx
%endif

#
# Allow the overriding of spl locations
#
%if %{defined require_splver}
%define splver %{require_splver}
%else
%define splver %{version}
%endif

%if %{defined require_spldir}
%define spldir %{require_spldir}
%else
%define spldir %{_usrsrc}/spl-%{splver}
%endif

%if %{defined require_splobj}
%define splobj %{require_splobj}
%else
%define splobj %{spldir}/${kernel_version%%___*}
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
        --with-spl="%{spldir}" \
        --with-spl-obj="%{splobj}" \
        %{debug} \
        %{debug_dmu_tx}
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

%changelog
* Fri Feb 22 2019 Tony Hutter <hutter2@llnl.gov> - 0.7.13-1
- Released 0.7.13-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.13
* Thu Nov 08 2018 Tony Hutter <hutter2@llnl.gov> - 0.7.12-1
- Released 0.7.12-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.12
* Thu Sep 13 2018 Tony Hutter <hutter2@llnl.gov> - 0.7.11-1
- Released 0.7.11-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.11
* Wed Sep 05 2018 Tony Hutter <hutter2@llnl.gov> - 0.7.10-1
- Released 0.7.10-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.10
* Tue May 08 2018 Tony Hutter <hutter2@llnl.gov> - 0.7.9-1
- Released 0.7.9-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.9
* Mon Apr 09 2018 Tony Hutter <hutter2@llnl.gov> - 0.7.8-1
- Released 0.7.8-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.8
* Wed Mar 14 2018 Tony Hutter <hutter2@llnl.gov> - 0.7.7-1
- Released 0.7.7-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.7
* Thu Feb 01 2018 Tony Hutter <hutter2@llnl.gov> - 0.7.6-1
- Released 0.7.6-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.6
* Mon Dec 18 2017 Tony Hutter <hutter2@llnl.gov> - 0.7.5-1
- Released 0.7.5-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.5
* Thu Dec 07 2017 Tony Hutter <hutter2@llnl.gov> - 0.7.4-1
- Released 0.7.4-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.4
* Wed Oct 18 2017 Tony Hutter <hutter2@llnl.gov> - 0.7.3-1
- Released 0.7.3-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.3
* Fri Sep 22 2017 Tony Hutter <hutter2@llnl.gov> - 0.7.2-1
- Released 0.7.2-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.2
* Tue Aug 8 2017 Tony Hutter <hutter2@llnl.gov> - 0.7.1-1
- Released 0.7.1-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.1
* Wed Jul 26 2017 Brian Behlendorf <behlendorf1@llnl.gov> - 0.7.0-1
- Released 0.7.0-1, detailed release notes are available at:
- https://github.com/zfsonlinux/zfs/releases/tag/zfs-0.7.0
