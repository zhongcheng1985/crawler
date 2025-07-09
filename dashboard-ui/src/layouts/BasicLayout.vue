<template>
  <a-layout class="layout">
    <!-- Top Navigation Bar -->
    <a-layout-header class="header">
      <div class="logo-area" :style="{ width: collapsed ? '80px' : '200px' }">
        <div class="logo">
          <img src="@/assets/logo.svg" alt="Crawler Dashboard ">
          <h1 v-show="!collapsed">Crawler Dashboard</h1>
        </div>
      </div>
      <div class="nav-content">
        <div class="left-menu">
          <a-button type="text" @click="toggleCollapse" class="collapse-btn">
            <menu-unfold-outlined v-if="collapsed" />
            <menu-fold-outlined v-else />
          </a-button>
        </div>
        <div class="right-menu">
          <a-dropdown>
            <template #overlay>
              <!-- <a-menu>
                <a-menu-item @click="handleLogout">Logout</a-menu-item>
              </a-menu> -->
            </template>
            <a-avatar :src="avatarImage" />
          </a-dropdown>
        </div>
      </div>
    </a-layout-header>

    <a-layout>
      <!-- Sidebar (Dark Background) -->
      <a-layout-sider 
        v-model:collapsed="collapsed"
        :trigger="null"
        collapsible
        width="200"
        theme="dark"
        class="sider"
      >
        <a-menu
          v-model:selectedKeys="selectedKeys"
          v-model:openKeys="openKeys"
          mode="inline"
          theme="dark"
        >
          <!-- <a-sub-menu key="monitor">
            <template #title>
              <span><monitor-outlined /><span v-if="!collapsed">Monitor Management</span></span>
            </template>
            <a-menu-item key="crawler">
              <router-link to="/crawler"><desktop-outlined /><span v-if="!collapsed">Crawler List</span></router-link>
            </a-menu-item>
            <a-menu-item key="session">
              <router-link to="/session"><api-outlined /><span v-if="!collapsed">Session List</span></router-link>
            </a-menu-item>
            <a-menu-item key="log">
              <router-link to="/log"><file-text-outlined /><span v-if="!collapsed">Log List</span></router-link>
            </a-menu-item>
          </a-sub-menu> -->

          <a-menu-item key="crawler">
            <router-link to="/crawler"><desktop-outlined /><span v-if="!collapsed">Crawler</span></router-link>
          </a-menu-item>
          <a-menu-item key="session">
            <router-link to="/session"><api-outlined /><span v-if="!collapsed">Session</span></router-link>
          </a-menu-item>
          <a-menu-item key="log">
            <router-link to="/log"><file-text-outlined /><span v-if="!collapsed">Log</span></router-link>
          </a-menu-item>
        </a-menu>
      </a-layout-sider>

      <!-- Content Area -->
      <a-layout style="padding: 0 24px 24px; height: 100%; display: flex; flex-direction: column;">
        <a-breadcrumb style="margin: 16px 0">
          <a-breadcrumb-item>Home</a-breadcrumb-item>
          <a-breadcrumb-item>{{ currentRouteName }}</a-breadcrumb-item>
        </a-breadcrumb>
        <a-layout-content class="content" style="flex: 1 1 0; min-height: 0;">
          <router-view />
        </a-layout-content>
        <!-- Footer -->
        <a-layout-footer class="footer">
          Crawler Dashboard ©2025
        </a-layout-footer>
      </a-layout>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { 
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  DesktopOutlined,
  ApiOutlined,
  FileTextOutlined 
} from '@ant-design/icons-vue'
import avatarImage from '@/assets/images/avatar.jpg'

const route = useRoute()
const collapsed = ref(false)
const selectedKeys = ref([route.path.replace(/^\//, '')])
const openKeys = ref(['monitor'])

const currentRouteName = computed(() => {
  return route.meta?.title || route.name
})

const toggleCollapse = () => {
  collapsed.value = !collapsed.value
  // Manually trigger resize event to ensure correct layout
  window.dispatchEvent(new Event('resize'))
}

const handleLogout = () => {
  console.log('Logout')
}

// Ensure menu selection updates automatically with route changes
watch(() => route.path, (newPath) => {
  selectedKeys.value = [newPath.replace(/^\//, '')]
})
</script>

<style scoped>
.layout {
  min-height: 100vh;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  padding: 0;
  background: white;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 1;
  position: relative;
}

/* LOGO Area - Dark Blue Background */
.logo-area {
  background: #001529;
  transition: width 0.2s;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo {
  display: flex;
  align-items: center;
  height: 64px;
  padding: 0 16px;
}

.logo img {
  height: 28px;
  margin-right: 0;
  display: block;
  margin-left: auto;
  margin-right: auto;
}

.logo h1 {
  margin: 0;
  font-size: 18px;
  color: white;
  white-space: nowrap;
}

/* Navigation Content Area - White Background */
.nav-content {
  display: flex;
  flex: 1;
  justify-content: space-between;
  background: white;
}

.left-menu {
  display: flex;
  align-items: center;
  padding-left: 16px;
}

.right-menu {
  display: flex;
  align-items: center;
  padding-right: 24px;
}

.collapse-btn {
  font-size: 16px;
  color: rgba(0, 0, 0, 0.65);
}

.collapse-btn:hover {
  color: #1890ff;
}

/* Collapsed State */
.layout .ant-layout-sider-collapsed + .ant-layout .header .logo-container {
  width: 80px;
}

.sider {
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  position: relative;
  z-index: 10;
}

.content {
  padding: 24px;
  background: #fff;
  flex: 1 1 0;
  min-height: 0;
}

.footer {
  text-align: center;
  padding: 16px 0;
  color: rgba(0, 0, 0, 0.65);
  background: #fff;
}
</style>