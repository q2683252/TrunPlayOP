#
# LuCI App TrunPlay - OpenWrt Package Makefile
#

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-trunplay
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

PKG_LICENSE:=MIT
PKG_MAINTAINER:=TrunPlay <trunplay@example.com>

LUCI_TITLE:=LuCI TrunPlay - Scheduled DLNA Media Casting
LUCI_DEPENDS:=+trunplay-backend +luci-base
LUCI_PKGARCH:=all

include $(TOPDIR)/feeds/luci/luci.mk

define Package/luci-app-trunplay/description
  LuCI web interface for TrunPlay scheduled DLNA media casting service.
  Provides management UI for playback plans, devices, SMB servers, and study tasks.
endef

# call BuildPackage - OpenWrt buildance Luci applications
$(eval $(call BuildPackage,luci-app-trunplay))
