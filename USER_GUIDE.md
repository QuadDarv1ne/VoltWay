# VoltWay User Guide

## Getting Started

VoltWay is an interactive map application for finding electric vehicle charging stations with advanced features like favorites and real-time notifications.

## Web Interface

### Main Features

#### 1. Map View
- Interactive map showing charging station locations
- Clustered markers for better visualization
- Automatic geolocation detection

#### 2. Search Controls
Located at the top of the page:
- **Latitude/Longitude**: Enter coordinates to search
- **Radius (km)**: Set search radius (default: 10km)
- **Search Button**: Trigger location-based search
- **Connector Filter**: Filter by connector type (CCS, CHAdeMO, Type 2)
- **Update Cache**: Refresh station data from external sources

#### 3. Station Information
Click on any station marker to view:
- Station name and address
- Connector type and power rating
- Current status (available/occupied/maintenance)
- Pricing information
- Operating hours
- **Favorite Button**: Save station to favorites
- **Subscribe Button**: Get real-time notifications

### Using Favorites

1. **Adding to Favorites**: 
   - Click on a station marker
   - Click the "☆ В избранное" button
   - Button turns gold (★ В избранном) when favorited

2. **Removing from Favorites**:
   - Click the gold favorite button again
   - Button returns to gray state

### Real-time Notifications

1. **Subscribing to Stations**:
   - Click on a station marker
   - Click the "🔔 Подписаться" button
   - Button turns green when subscribed

2. **Receiving Notifications**:
   - Desktop notifications appear at top-right
   - Auto-dismiss after 5 seconds
   - Shows station status changes

3. **Unsubscribing**:
   - Click the green subscribe button again
   - Button turns red indicating unsubscribed state

## Mobile Usage

The interface is fully responsive and works on mobile devices:
- Touch-friendly controls
- Optimized layout for small screens
- Mobile-optimized notifications

## Keyboard Shortcuts

- **Enter**: Trigger search when focus is on search inputs
- **Esc**: Close popups and notifications

## Troubleshooting

### Map Not Loading
- Check internet connection
- Refresh the page
- Clear browser cache

### Geolocation Not Working
- Ensure browser location permissions are granted
- Check if location services are enabled on device

### Notifications Not Appearing
- Check browser notification permissions
- Ensure WebSocket connection is active (look for connection status message)

### Search Returns No Results
- Try increasing the radius
- Verify coordinates are correct
- Check if filters are too restrictive

## Performance Tips

1. **Optimize Searches**:
   - Use reasonable radius values (1-50km)
   - Apply specific filters to reduce results
   - Don't search too frequently

2. **Manage Subscriptions**:
   - Unsubscribe from stations you don't need updates for
   - Too many subscriptions may impact performance

3. **Browser Recommendations**:
   - Use modern browsers (Chrome, Firefox, Edge)
   - Keep browser updated
   - Disable unnecessary extensions

## Privacy and Security

### Data Collection
- Location data is used only for finding nearby stations
- Favorite selections are stored securely
- No personal driving data is collected

### Authentication
- User accounts are password-protected
- Passwords are securely hashed
- Session tokens expire automatically

## Technical Requirements

### Browser Support
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

### System Requirements
- Modern computer or mobile device
- Stable internet connection
- JavaScript enabled
- Cookies enabled for authentication

## API Access

For developers wanting to integrate VoltWay data:
- See `API_DOCUMENTATION.md` for full API specification
- All endpoints are RESTful
- JSON format responses
- Authentication required for most operations

## Reporting Issues

If you encounter problems:
1. Note the error message
2. Record the steps that led to the issue
3. Include browser/device information
4. Contact support with this information

## Feature Requests

We welcome suggestions for new features:
- Submit ideas through our feedback system
- Popular requests may be prioritized for development
- Community input helps shape future improvements

## Updates and Maintenance

- Regular updates add new stations and features
- Database is refreshed periodically
- Monitor the health endpoint for service status
- Check release notes for new functionality

## Best Practices

1. **Efficient Searching**:
   - Start with smaller radius and expand if needed
   - Use connector filters when you know your vehicle's requirements
   - Save frequently used locations as favorites

2. **Battery Management**:
   - Subscribe to stations along your planned route
   - Check station availability before departure
   - Have backup charging options identified

3. **Navigation**:
   - Combine with navigation apps for turn-by-turn directions
   - Verify station hours match your arrival time
   - Check pricing before charging sessions

## Accessibility

The application follows accessibility best practices:
- Keyboard navigable interface
- Screen reader compatible
- High contrast elements
- Adjustable text sizes

## Data Sources

Station information comes from:
- Open Charge Map API
- Manual submissions
- User contributions
- Official charging network data

Data is regularly validated and updated to ensure accuracy.