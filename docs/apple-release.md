# Apple build release procedure

This repository provides the shared App Store Connect and TestFlight upload step used by app repositories. Each app keeps its native build and signing adapter; the release sequence after a release is explicitly authorized is the same for every app.

## Release sequence

1. **Preflight the release.** Confirm the App Store Connect app record, platform, bundle identifier, marketing version, and next build number. Confirm the record has the required store metadata and an app icon in the native target. Do not start an upload when the app identity or icon is missing.
2. **Build and sign natively.** Use the app's existing Xcode, Swift, or Flutter/Xcode build. Expo apps use prebuild and Xcode. Export the store-ready artifact and retain the build logs and artifact for the release record.
3. **Validate the artifact in the app adapter.** Check the bundle identifier, version/build number, signature, and packaged icon against the release inputs. Fail before upload on any mismatch. The shared upload action currently enforces the artifact path/platform/backend contract; app adapters own these app-specific checks.
4. **Upload through the shared action.** Keep the caller's explicit release gate and protected environment. The action uploads the package and waits for App Store Connect processing by default.
5. **Verify in App Store Connect.** Confirm the expected platform, version, and build number appear under TestFlight. Verify the app icon is rendered for the app/build as expected. Record the successful processed build and its source commit.
6. **Continue distribution deliberately.** TestFlight group assignment, export compliance changes, and App Review submission remain explicit app release steps. A successful upload does not perform them.

Do not use a hosted build service as a hidden prerequisite. In particular, Expo apps that do not have EAS Build access use Expo prebuild and the repository's Xcode build/export workflow.

## Artifact contract

| Platform | Caller provides | Upload backend |
| --- | --- | --- |
| iOS | Signed `.ipa` | `appstore-api` |
| macOS App Store | Signed `.pkg` | `altool` (or `transporter`) |

The action rejects unsupported file/platform/backend combinations and waits for App Store Connect processing by default. A successful upload step means Apple accepted and processed that build, not that it was submitted for review or released. The action never submits a build for App Review or assigns a TestFlight group.

## Credential names

Use these repository or organization Actions values when adopting the shared step:

- Variable `APPSTORE_ISSUER_ID`
- Variable `APPSTORE_API_KEY_ID`
- Secret `APPSTORE_API_PRIVATE_KEY`

Do not store the `.p8` key in a repository. Existing app-specific names can be mapped at the call site during migration; credentials are passed to the action as inputs and are not written by this action to disk.

## Example: iOS IPA

```yaml
- name: Upload and wait for processing
  id: testflight
  uses: rckt-corp/.github/actions/apple-testflight-upload@<reviewed-ref>
  with:
    app-path: apps/frontend/build-output.ipa
    app-type: ios
    backend: appstore-api
    issuer-id: ${{ vars.APPSTORE_ISSUER_ID }}
    api-key-id: ${{ vars.APPSTORE_API_KEY_ID }}
    api-private-key: ${{ secrets.APPSTORE_API_PRIVATE_KEY }}
    uses-non-exempt-encryption: "false"
```

## Example: macOS App Store package

```yaml
- name: Upload and wait for processing
  id: testflight
  uses: rckt-corp/.github/actions/apple-testflight-upload@<reviewed-ref>
  with:
    app-path: dist/Expunge-0.1.28.pkg
    app-type: macos
    backend: altool
    issuer-id: ${{ vars.APPSTORE_ISSUER_ID }}
    api-key-id: ${{ vars.APPSTORE_API_KEY_ID }}
    api-private-key: ${{ secrets.APPSTORE_API_PRIVATE_KEY }}
```

Replace `<reviewed-ref>` with the immutable commit SHA or reviewed release tag for this action. Keep the caller's protected release environment and explicit upload gate; the shared action standardizes transport and processing checks, not when a release is authorized.

## Build adapters stay native

The common action does not build or sign applications. Callers produce their normal store-ready artifact with the platform's own toolchain, for example:

- Expunge: Swift app bundle, App Store signing, then `.pkg` packaging.
- Codae: Flutter iOS archive and exported `.ipa`.
- Expo/React Native apps: Expo prebuild plus CocoaPods and Xcode archive/export, without a hosted EAS build dependency.

Every build adapter should verify bundle ID, marketing version, build number, signature, and the packaged app icon before invoking the upload action.
