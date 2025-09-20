import React from 'react';
import { Box, Stack,IconButton } from '@mui/material';
import LinkedInIcon from '@mui/icons-material/LinkedIn';
import XIcon from '@mui/icons-material/X';
import GitHubIcon from '@mui/icons-material/GitHub';


function SocialMedia() {
    return (
        <Box sx={{ paddingRight:5, paddingTop:2 }}>
        <Stack direction="row" spacing={2}>
            <IconButton 
                component="a" 
                href="https://www.linkedin.com" 
                target="_blank" 
                rel="noopener noreferrer" 
                sx={{ color: 'purple' }}
            >
                <LinkedInIcon />
            </IconButton>
            <IconButton 
                component="a" 
                href="https://twitter.com" 
                target="_blank" 
                rel="noopener noreferrer" 
                sx={{ color: 'purple' }}
            >
                <XIcon />
            </IconButton>
            <IconButton 
                component="a" 
                href="https://github.com" 
                target="_blank" 
                rel="noopener noreferrer" 
                sx={{ color: 'purple' }}
            >
                <GitHubIcon />
            </IconButton>
        </Stack>
    </Box>
    );

}
export default SocialMedia;