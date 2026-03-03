-- TrunPlay LuCI Controller
-- Routes for TrunPlay DLNA Casting application

module("luci.controller.trunplay", package.seeall)

function index()
    -- Main entry point under Services menu
    entry({"admin", "services", "trunplay"}, alias("admin", "services", "trunplay", "home"), _("TrunPlay 定时投屏"), 80)

    -- Status/Home page
    entry({"admin", "services", "trunplay", "home"}, template("trunplay/home"), _("状态总览"), 1)

    -- Plans management
    entry({"admin", "services", "trunplay", "plans"}, template("trunplay/plans"), _("播放计划"), 2)

    -- Devices management
    entry({"admin", "services", "trunplay", "devices"}, template("trunplay/devices"), _("设备管理"), 3)

    -- SMB servers management
    entry({"admin", "services", "trunplay", "smb"}, template("trunplay/smb"), _("SMB 存储"), 4)

    -- Study tasks management
    entry({"admin", "services", "trunplay", "study"}, template("trunplay/study"), _("学习任务"), 5)

    -- Playback history
    entry({"admin", "services", "trunplay", "history"}, template("trunplay/history"), _("播放历史"), 6)

    -- Settings
    entry({"admin", "services", "trunplay", "settings"}, template("trunplay/settings"), _("设置"), 7)

    -- API proxy endpoints (for AJAX calls from LuCI)
    entry({"admin", "services", "trunplay", "api"}, call("api_proxy"), nil).leaf = true
end

-- API proxy function to forward requests to backend
function api_proxy()
    local http = require "luci.http"
    local sys = require "luci.sys"
    local json = require "luci.jsonc"

    -- Get path parameter from form data
    local path = http.formvalue("path")
    -- Ensure path is a string, not a table
    if type(path) == "table" then
        path = path[1] or ""
    elseif not path then
        path = ""
    end

    -- Get method from form data (frontend always POSTs but includes actual method in form)
    local method = http.formvalue("method")
    if type(method) == "table" then
        method = method[1]
    end
    -- Default to GET if not specified
    method = method or "GET"
    method = string.upper(method)

    -- Build backend URL
    local backend_url = "http://127.0.0.1:8088/api/v1" .. path

    -- Forward request using curl
    local cmd
    if method == "GET" then
        cmd = string.format("curl -s '%s'", backend_url)
    elseif method == "POST" then
        local body = http.formvalue("body")
        if type(body) == "table" then
            body = body[1] or "{}"
        elseif not body then
            body = "{}"
        end
        -- Escape single quotes in body for shell command
        body = string.gsub(body, "'", "'\\''")
        cmd = string.format("curl -s -X POST -H 'Content-Type: application/json' -d '%s' '%s'", body, backend_url)
    elseif method == "PUT" then
        local body = http.formvalue("body")
        if type(body) == "table" then
            body = body[1] or "{}"
        elseif not body then
            body = "{}"
        end
        -- Escape single quotes in body for shell command
        body = string.gsub(body, "'", "'\\''")
        cmd = string.format("curl -s -X PUT -H 'Content-Type: application/json' -d '%s' '%s'", body, backend_url)
    elseif method == "DELETE" then
        cmd = string.format("curl -s -X DELETE '%s'", backend_url)
    else
        http.status(405, "Method Not Allowed")
        http.prepare_content("application/json")
        http.write('{"error": "Method ' .. method .. ' not allowed"}')
        return
    end

    local result = sys.exec(cmd)

    http.prepare_content("application/json")
    http.write(result or '{"error": "Backend request failed"}')
end
