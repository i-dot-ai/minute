// Included to fix type issue in audio-player.tsx
// To support older browsers we support the case where webkitAudioContext is used instead of AudioContext
// Typescript doesn't include webkitAudioContext in it's type definition for Window.
// So here we add it.
declare interface Window {
  webkitAudioContext: typeof AudioContext
}
