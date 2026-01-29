#
# TrunPlay Backend - OpenWrt Package Makefile
#

include $(TOPDIR)/rules.mk

PKG_NAME:=trunplay-backend
PKG_VERSION:=1.0.0
PKG_RELEASE:=1

PKG_LICENSE:=MIT
PKG_MAINTAINER:=TrunPlay <trunplay@example.com>

include $(INCLUDE_DIR)/package.mk

define Package/trunplay-backend
  SECTION:=multimedia
  CATEGORY:=Multimedia
  TITLE:=TrunPlay Backend Service
  DEPENDS:=+python3 +python3-pip +python3-setuptools +python3-logging +python3-asyncio +python3-urllib +python3-email +python3-sqlite3
  PKGARCH:=all
endef

define Package/trunplay-backend/description
  TrunPlay backend service providing REST API for scheduled DLNA media casting.
  Features: DLNA device discovery, SMB file browsing, scheduled playback, media streaming.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src $(PKG_BUILD_DIR)/
	$(CP) ./root $(PKG_BUILD_DIR)/
	$(CP) ./requirements.txt $(PKG_BUILD_DIR)/
endef

define Build/Compile
endef

define Package/trunplay-backend/install
	# Install Python source files
	$(INSTALL_DIR) $(1)/usr/lib/trunplay
	$(CP) $(PKG_BUILD_DIR)/src/* $(1)/usr/lib/trunplay/

	# Install requirements.txt for pip install
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/requirements.txt $(1)/usr/lib/trunplay/

	# Install init script
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/root/etc/init.d/trunplay $(1)/etc/init.d/trunplay

	# Install trigger script
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/root/usr/bin/trunplay-trigger $(1)/usr/bin/trunplay-trigger

	# Install default config
	$(INSTALL_DIR) $(1)/etc/trunplay
	$(INSTALL_CONF) $(PKG_BUILD_DIR)/root/etc/trunplay/config.json $(1)/etc/trunplay/config.json
endef

define Package/trunplay-backend/postinst
#!/bin/sh
# Install Python dependencies
if [ -z "$${IPKG_INSTROOT}" ]; then
	echo "Installing Python dependencies..."
	pip3 install --no-deps -r /usr/lib/trunplay/requirements.txt 2>/dev/null || \
	pip3 install -r /usr/lib/trunplay/requirements.txt || \
	echo "Warning: Could not install Python dependencies. Please install manually."

	# Enable and start service
	/etc/init.d/trunplay enable
	/etc/init.d/trunplay start
fi
exit 0
endef

define Package/trunplay-backend/prerm
#!/bin/sh
if [ -z "$${IPKG_INSTROOT}" ]; then
	/etc/init.d/trunplay stop
	/etc/init.d/trunplay disable
fi
exit 0
endef

$(eval $(call BuildPackage,trunplay-backend))
