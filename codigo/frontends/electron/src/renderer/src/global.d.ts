import type { ApiTucoteca } from '../../shared/api'

declare global {
  interface Window {
    tucoteca: ApiTucoteca
  }
}
