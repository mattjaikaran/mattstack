"""Post-processor to configure frontend for monorepo integration."""

from __future__ import annotations

from mattstack.config import FrontendFramework, ProjectConfig
from mattstack.utils.console import print_info


def setup_frontend_monorepo(config: ProjectConfig) -> None:
    """Configure frontend .env for monorepo mode with Django backend."""
    if not config.has_frontend or not config.has_backend:
        return

    if config.is_nextjs:
        _setup_nextjs_monorepo(config)
    elif config.frontend_framework == FrontendFramework.REACT_RSBUILD:
        _setup_rsbuild_monorepo(config)
    else:
        _setup_vite_monorepo(config)


def _setup_vite_monorepo(config: ProjectConfig) -> None:
    """Configure Vite frontend .env for monorepo mode with Django backend."""
    env_file = config.frontend_dir / ".env"
    env_content = """\
VITE_MODE=django-spa
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_AUTH_TOKEN_KEY=access_token
VITE_REFRESH_TOKEN_KEY=refresh_token
VITE_ENABLE_MOCK_API=false
VITE_DJANGO_CSRF_TOKEN_NAME=csrftoken
VITE_DJANGO_STATIC_URL=/static/
VITE_DJANGO_MEDIA_URL=/media/
VITE_DJANGO_API_PREFIX=/api/v1
"""
    env_file.write_text(env_content)

    env_mono = config.frontend_dir / ".env.monorepo"
    env_mono.write_text(env_content)

    print_info("Configured frontend for monorepo mode")

    _create_vite_monorepo_config(config)


def _setup_nextjs_monorepo(config: ProjectConfig) -> None:
    """Configure Next.js frontend .env.local for monorepo mode with Django backend."""
    env_file = config.frontend_dir / ".env.local"
    env_content = """\
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_AUTH_TOKEN_KEY=access_token
NEXT_PUBLIC_REFRESH_TOKEN_KEY=refresh_token
"""
    env_file.write_text(env_content)

    print_info("Configured Next.js frontend for monorepo mode")

    _create_nextjs_monorepo_config(config)


def _create_vite_monorepo_config(config: ProjectConfig) -> None:
    """Create vite.config.monorepo.ts with Django proxy settings."""
    vite_config = config.frontend_dir / "vite.config.monorepo.ts"
    vite_config.write_text("""\
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/static": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        assetFileNames: "static/css/[name]-[hash][extname]",
        chunkFileNames: "static/js/[name]-[hash].js",
        entryFileNames: "static/js/[name]-[hash].js",
      },
    },
  },
});
""")
    print_info("Created vite.config.monorepo.ts with Django proxy")


def _create_nextjs_monorepo_config(config: ProjectConfig) -> None:
    """Create next.config.monorepo.ts with Django API rewrites."""
    next_config = config.frontend_dir / "next.config.monorepo.ts"
    next_config.write_text("""\
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
      {
        source: "/admin/:path*",
        destination: "http://localhost:8000/admin/:path*",
      },
      {
        source: "/static/:path*",
        destination: "http://localhost:8000/static/:path*",
      },
    ];
  },
};

export default nextConfig;
""")
    print_info("Created next.config.monorepo.ts with Django API rewrites")


def _setup_rsbuild_monorepo(config: ProjectConfig) -> None:
    """Configure Rsbuild frontend .env for monorepo mode with Django backend."""
    env_file = config.frontend_dir / ".env"
    env_content = """\
PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
PUBLIC_AUTH_TOKEN_KEY=access_token
PUBLIC_REFRESH_TOKEN_KEY=refresh_token
PUBLIC_ENABLE_MOCK_API=false
PUBLIC_DJANGO_CSRF_TOKEN_NAME=csrftoken
PUBLIC_DJANGO_STATIC_URL=/static/
PUBLIC_DJANGO_MEDIA_URL=/media/
PUBLIC_DJANGO_API_PREFIX=/api/v1
"""
    env_file.write_text(env_content)

    env_mono = config.frontend_dir / ".env.monorepo"
    env_mono.write_text(env_content)

    print_info("Configured Rsbuild frontend for monorepo mode")

    _create_rsbuild_monorepo_config(config)


def _create_rsbuild_monorepo_config(config: ProjectConfig) -> None:
    """Create rsbuild.config.monorepo.ts with Django proxy settings."""
    rsbuild_config = config.frontend_dir / "rsbuild.config.monorepo.ts"
    rsbuild_config.write_text("""\
import { defineConfig } from "@rsbuild/core";
import { pluginReact } from "@rsbuild/plugin-react";

export default defineConfig({
  plugins: [pluginReact()],
  source: {
    entry: {
      index: "./src/main.tsx",
    },
  },
  resolve: {
    alias: {
      "@": "./src",
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/static": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/admin": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
""")
    print_info("Created rsbuild.config.monorepo.ts with Django proxy")
