# Devify UI Architecture

## Overview

Devify UI is a modern single-page application built with Vue 3 and designed for overseas users. It provides a clean, responsive interface for managing chat analysis results and system configuration.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
├─────────────────────────────────────────────────────────────┤
│  Vue 3 Application (Composition API + <script setup>)      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Pages         │  │   Components    │  │   Router     │ │
│  │   - Login       │  │   - BaseButton  │  │   - Guards   │ │
│  │   - Dashboard   │  │   - BaseInput   │  │   - Routes   │ │
│  │   - Settings    │  │   - BaseCard    │  │              │ │
│  │   - NotFound    │  │   - BaseModal   │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  State Management (Pinia)                                  │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   User Store    │  │   Config Store  │                  │
│  │   - Auth        │  │   - SMTP Config │                  │
│  │   - Profile     │  │   - Settings    │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  API Layer (Axios)                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Auth API      │  │   Chat API      │  │   Config API │ │
│  │   - Login       │  │   - Results     │  │   - SMTP     │ │
│  │   - Profile     │  │   - Messages    │  │   - Settings │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Vite Development Server (Proxy to Backend)                │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend API                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Django REST   │  │   Authentication│  │   Database   │ │
│  │   Framework     │  │   - JWT Tokens  │  │   - SQLite   │ │
│  │   - Threadline  │  │   - Permissions │  │   - MySQL    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Authentication System
- JWT-based authentication
- Automatic token refresh
- Route guards for protected pages
- User profile management

### 2. Responsive Design
- Mobile-first approach
- Tailwind CSS utility classes
- Consistent component library
- Dark mode ready (planned)

### 3. State Management
- Pinia for global state
- Reactive data flow
- Persistent storage for user data
- Error handling and loading states

### 4. API Integration
- Axios with interceptors
- Automatic token attachment
- Error handling and retries
- Request/response transformation

## Component Architecture

### Base Components
- **BaseButton**: Consistent button styling with variants
- **BaseInput**: Form input with validation and error states
- **BaseCard**: Container component with header/body/footer
- **BaseModal**: Accessible modal dialog component

### Layout Components
- **AppLayout**: Main application layout wrapper
- **AppHeader**: Navigation header with user menu

### Page Components
- **Login**: Authentication form with validation
- **Dashboard**: Data overview with statistics and results
- **Settings**: Configuration management interface
- **NotFound**: 404 error page

## Data Flow

1. **User Interaction** → Component Event
2. **Component** → Store Action
3. **Store Action** → API Call
4. **API Response** → Store State Update
5. **Store State** → Component Reactivity
6. **Component** → UI Update

## Security Considerations

- JWT tokens stored in localStorage
- Automatic token refresh on API calls
- Route guards prevent unauthorized access
- Input validation on all forms
- XSS protection through Vue's template system

## Performance Optimizations

- Lazy loading for route components
- Vite for fast development and building
- Tree shaking for smaller bundle size
- Optimized images and assets
- Efficient state management with Pinia

## Browser Support

- Modern browsers (Chrome 88+, Firefox 85+, Safari 14+)
- Mobile browsers (iOS Safari 14+, Chrome Mobile 88+)
- Progressive enhancement for older browsers

## Development Workflow

1. **Development**: `npm run dev` - Hot reload development server
2. **Linting**: `npm run lint` - Code quality checks
3. **Building**: `npm run build` - Production build
4. **Preview**: `npm run preview` - Preview production build

## Deployment

The application is designed to be deployed as a static site with API proxying to the backend. It can be served from any static file server or CDN.
